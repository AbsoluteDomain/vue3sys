/**
 * 登录后版本更新弹窗
 */
import { ref } from "vue";
import { useUserStore } from "@/store";
import ReleaseAPI, { type ReleaseDetail } from "@/api/system/release";

const loginPopupVisible = ref(false);
const loginPopupDetail = ref<ReleaseDetail | null>(null);
let lastCheckedUserId: string | number | null = null;

export function useReleaseLoginPopup() {
  async function checkAndShowLoginPopup() {
    const userId = useUserStore().userInfo?.userId;
    if (!userId) return;
    if (lastCheckedUserId === userId) return;
    lastCheckedUserId = userId;

    try {
      const data = await ReleaseAPI.getLatestUnread();
      if (data?.id) {
        loginPopupDetail.value = data;
        loginPopupVisible.value = true;
      }
    } catch {
      // 静默失败，不影响主流程
    }
  }

  async function dismissLoginPopup() {
    const id = loginPopupDetail.value?.id;
    loginPopupVisible.value = false;
    if (id) {
      try {
        await ReleaseAPI.markRead(id);
      } catch {
        // ignore
      }
    }
    loginPopupDetail.value = null;
  }

  function resetReleaseLoginCheck() {
    lastCheckedUserId = null;
    loginPopupVisible.value = false;
    loginPopupDetail.value = null;
  }

  return {
    loginPopupVisible,
    loginPopupDetail,
    checkAndShowLoginPopup,
    dismissLoginPopup,
    resetReleaseLoginCheck,
  };
}
