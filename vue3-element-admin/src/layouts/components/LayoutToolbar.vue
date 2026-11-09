<template>
  <div :class="['navbar-actions', navbarActionsClass]">
    <!-- 桌面端工具项 -->
    <template v-if="isDesktop">
      <!-- 搜索 -->
      <div class="navbar-actions__item">
        <CommandPalette />
      </div>

      <!-- 全屏 -->
      <div class="navbar-actions__item">
        <Fullscreen />
      </div>

      <!-- 布局大小 -->
      <div class="navbar-actions__item">
        <SizeSelect />
      </div>

      <!-- 语言选择 -->
      <div class="navbar-actions__item">
        <LangSelect />
      </div>

      <!-- 通知 -->
      <div class="navbar-actions__item">
        <NoticeDropdown />
      </div>

      <!-- 版本更新 -->
      <div class="navbar-actions__item">
        <ReleaseDropdown />
      </div>

      <!-- 租户选择（如果启用多租户）-->
      <div v-if="showTenantSwitcher" class="navbar-actions__item">
        <TenantSwitcher @change="handleTenantChange" />
      </div>
    </template>

    <!-- 用户菜单 -->
    <div class="navbar-actions__item">
      <el-dropdown trigger="click" @visible-change="handleDropdownVisible">
        <div class="user-profile">
          <el-badge
            :value="pendingApprovalCount"
            :hidden="pendingApprovalCount === 0"
            :max="99"
            class="user-profile__badge"
          >
            <el-avatar
              :size="28"
              :src="userStore.userInfo.avatar || undefined"
              class="user-profile__avatar"
            >
              {{ userInitial }}
            </el-avatar>
          </el-badge>
          <span class="user-profile__name">{{ userStore.userInfo.nickname }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="handleProfileClick">
              {{ t("navbar.profile") }}
            </el-dropdown-item>
            <el-dropdown-item @click="handleMyApprovalClick">
              我的审批
              <span v-if="pendingApprovalCount > 0" class="approval-count">{{ pendingApprovalCount }}</span>
            </el-dropdown-item>
            <el-dropdown-item divided @click="logout">
              {{ t("navbar.logout") }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- 系统设置 -->
    <div v-if="defaults.showSettings" class="navbar-actions__item" @click="handleSettingsClick">
      <div class="i-svg:setting" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { defaults } from "@/settings";
import { DeviceEnum, SidebarColor, ThemeMode, LayoutMode } from "@/enums/settings";
import { useAppStore, useSettingsStore, useUserStore } from "@/store";

// 导入子组件
import CommandPalette from "@/components/CommandPalette/index.vue";
import Fullscreen from "@/components/Fullscreen/index.vue";
import SizeSelect from "@/components/SizeSelect/index.vue";
import LangSelect from "@/components/LangSelect/index.vue";
import NoticeDropdown from "@/components/NoticeDropdown/index.vue";
import ReleaseDropdown from "@/components/ReleaseDropdown/index.vue";
import TenantSwitcher from "@/components/TenantSwitcher/index.vue";
import { useTenantStoreHook } from "@/store/modules/tenant";
import ApprovalAPI from "@/api/approval";

const { t } = useI18n();
const appStore = useAppStore();
const settingStore = useSettingsStore();
const userStore = useUserStore();
const tenantStore = useTenantStoreHook();

const route = useRoute();
const router = useRouter();

// 用户名首字，用作头像未设置或加载失败时的兜底显示
const userInitial = computed(() => {
  const name = userStore.userInfo.nickname || userStore.userInfo.username || "";
  return name.charAt(0).toUpperCase();
});

// 是否为桌面设备
const isDesktop = computed(() => appStore.device === DeviceEnum.DESKTOP);

const canSwitchTenant = computed(() => userStore.userInfo?.canSwitchTenant === true);

// 是否显示租户选择
const showTenantSwitcher = computed(() => {
  if (!canSwitchTenant.value) {
    return false;
  }
  return tenantStore.tenantList.length > 1;
});

function handleTenantChange(tenantId: number) {
  tenantStore.switchTenant(tenantId).then(
    () => {
      ElMessage.success("切换租户成功");
      window.location.href = "/";
    },
    (error: any) => {
      ElMessage.error(error.message || "切换租户失败");
    }
  );
}

/**
 * 打开个人中心页面
 */
function handleProfileClick() {
  router.push({ name: "Profile" });
}

// 待我审批数量
const pendingApprovalCount = ref(0);
// 已提示过的最新审批申请 ID，用于识别「是否有新申请到达」
let lastSeenRequestId = 0;
let approvalPollTimer: ReturnType<typeof setInterval> | undefined;

async function loadPendingApprovalCount(notify = true) {
  try {
    const result = await ApprovalAPI.getMyTaskCount();
    const count = result?.count || 0;
    const latest = result?.latest || null;
    pendingApprovalCount.value = count;

    // 申请 ID 自增，出现更大的 ID 说明有新的待审批申请
    const latestId = latest?.id || 0;
    if (notify && latestId > lastSeenRequestId) {
      ElNotification({
        title: "新的待审批消息",
        message: latest
          ? `${latest.applicant_name || "有用户"} 提交了「${latest.name}」审批：${latest.summary}，共 ${count} 条待处理`
          : `您有 ${count} 条待审批申请需要处理`,
        type: "warning",
        position: "bottom-right",
        duration: 8000,
        onClick: () => handleMyApprovalClick(),
      });
    }
    if (latestId > lastSeenRequestId) {
      lastSeenRequestId = latestId;
    }
  } catch {
    pendingApprovalCount.value = 0;
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === "visible") {
    loadPendingApprovalCount();
  }
}

function handleDropdownVisible(visible: boolean) {
  if (visible) {
    loadPendingApprovalCount();
  }
}

function handleMyApprovalClick() {
  router.push({ name: "MyApprovalTasks" });
}

onMounted(() => {
  // 首次加载只记录基线，不弹提示，避免历史待办重复打扰
  loadPendingApprovalCount(false);
  // 轮询待审批数量：有新申请到达时弹出通知提示
  approvalPollTimer = setInterval(() => loadPendingApprovalCount(), 30000);
  document.addEventListener("visibilitychange", handleVisibilityChange);
});

onBeforeUnmount(() => {
  if (approvalPollTimer) {
    clearInterval(approvalPollTimer);
    approvalPollTimer = undefined;
  }
  document.removeEventListener("visibilitychange", handleVisibilityChange);
});

// 根据主题和侧边栏配色方案选择样式类
const navbarActionsClass = computed(() => {
  const { theme, sidebarColorScheme, layout } = settingStore;

  // 暗黑主题下，所有布局都使用白色文字
  if (theme === ThemeMode.DARK) {
    return "navbar-actions--white-text";
  }

  // 明亮主题下
  if (theme === ThemeMode.LIGHT) {
    // 顶部布局和混合布局的顶部区域：
    // - 如果侧边栏是经典蓝色，使用白色文字
    // - 如果侧边栏是极简白色，使用深色文字
    if (layout === LayoutMode.TOP || layout === LayoutMode.MIX) {
      if (sidebarColorScheme === SidebarColor.CLASSIC_BLUE) {
        return "navbar-actions--white-text";
      } else {
        return "navbar-actions--dark-text";
      }
    }
  }

  return "navbar-actions--dark-text";
});

/**
 * 退出登录
 */
function logout() {
  ElMessageBox.confirm("确定注销并退出系统吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
    lockScroll: false,
  }).then(() => {
    userStore.logout().then(() => {
      router.push(`/login?redirect=${route.fullPath}`);
    });
  });
}

/**
 * 打开系统设置页面
 */
function handleSettingsClick() {
  settingStore.settingsVisible = true;
}
</script>

<style lang="scss" scoped>
.navbar-actions {
  display: flex;
  align-items: center;
  min-height: 44px;

  &__item {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 44px; /* 增加最小点击区域到44px，符合人机交互标准 */
    height: 44px;
    padding: 0 8px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s;

    // 确保子元素居中
    > * {
      display: flex;
      align-items: center;
      justify-content: center;
    }

    // 确保 Element Plus 组件可以正常工作
    :deep(.el-dropdown),
    :deep(.el-tooltip) {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 44px;
    }

    :deep(.i-svg\:language) {
      flex-shrink: 0;
      width: 18px;
      height: 18px;
      font-size: 18px;
      line-height: 18px;
      background-size: 18px 18px;
    }

    // 图标样式
    :deep([class^="i-svg:"]) {
      font-size: 18px;
      line-height: 1;
      color: var(--el-text-color-regular);
      transition: color 0.3s;
    }

    &:hover {
      background: var(--el-fill-color-light);

      :deep([class^="i-svg:"]) {
        color: var(--el-color-primary);
      }
    }
  }

  .user-profile {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 44px;
    padding: 0 8px;

    &__avatar {
      flex-shrink: 0;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background-color: var(--el-color-primary);
      color: var(--el-color-white);
      font-size: 14px;
      font-weight: 600;
    }

    &__badge {
      display: flex;
      align-items: center;

      :deep(.el-badge__content) {
        top: 5px;
        right: 6px;
      }
    }

    &__name {
      margin-left: 8px;
      color: var(--el-text-color-regular);
      white-space: nowrap;
      transition: color 0.3s;
    }
  }

  .approval-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    margin-left: 6px;
    font-size: 12px;
    line-height: 1;
    color: var(--el-color-white);
    background: var(--el-color-danger);
    border-radius: 9px;
  }
}

// 白色文字样式（用于深色背景：暗黑主题、顶部布局、混合布局等）
.navbar-actions--white-text {
  .navbar-actions__item {
    :deep([class^="i-svg:"]) {
      color: color-mix(in srgb, var(--el-color-white) 85%, transparent);
    }

    &:hover {
      background: color-mix(in srgb, var(--el-color-white) 10%, transparent);

      :deep([class^="i-svg:"]) {
        color: var(--el-color-white);
      }
    }
  }

  .user-profile__name {
    color: color-mix(in srgb, var(--el-color-white) 85%, transparent);
  }

  // 租户选择器在白色文字模式下的样式
  ::v-deep(.tenant-switcher__trigger) {
    color: color-mix(in srgb, var(--el-color-white) 85%, transparent);
  }
  ::v-deep(.tenant-switcher__trigger .tenant-switcher__icon) {
    color: color-mix(in srgb, var(--el-color-white) 85%, transparent);
  }
  ::v-deep(.tenant-switcher__trigger:hover) {
    color: var(--el-color-white);
    background: color-mix(in srgb, var(--el-color-white) 10%, transparent);
  }
  ::v-deep(.tenant-switcher__trigger:hover .tenant-switcher__icon) {
    color: var(--el-color-white);
  }
}

// 深色文字样式（用于浅色背景：明亮主题下的左侧布局等）
.navbar-actions--dark-text {
  .navbar-actions__item {
    :deep([class^="i-svg:"]) {
      color: var(--el-text-color-regular) !important;
    }

    &:hover {
      background: rgba(0, 0, 0, 0.04);

      :deep([class^="i-svg:"]) {
        color: var(--el-color-primary) !important;
      }
    }
  }

  .user-profile__name {
    color: var(--el-text-color-regular) !important;
  }

  // 租户选择器在深色文字模式下的样式
  ::v-deep(.tenant-switcher__trigger) {
    color: var(--el-text-color-regular) !important;
  }
  ::v-deep(.tenant-switcher__trigger .tenant-switcher__icon) {
    color: var(--el-text-color-regular) !important;
  }
  ::v-deep(.tenant-switcher__trigger:hover) {
    color: var(--el-color-primary) !important;
    background: var(--el-fill-color-light);
  }
  ::v-deep(.tenant-switcher__trigger:hover .tenant-switcher__icon) {
    color: var(--el-color-primary) !important;
  }
}

// 确保下拉菜单中的图标不受影响
::v-deep(.el-dropdown-menu) {
  [class^="i-svg:"] {
    color: var(--el-text-color-regular) !important;

    &:hover {
      color: var(--el-color-primary) !important;
    }
  }
}
</style>
