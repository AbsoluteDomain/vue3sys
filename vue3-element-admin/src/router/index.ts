import type { App } from "vue";
import { createRouter, createWebHashHistory, type RouteRecordRaw } from "vue-router";

export const Layout = () => import("@/layouts/index.vue");

// 静态路由
export const constantRoutes: RouteRecordRaw[] = [
  {
    path: "/redirect",
    component: Layout,
    meta: { hidden: true },
    children: [
      {
        path: "/redirect/:path(.*)",
        component: () => import("@/views/redirect/index.vue"),
      },
    ],
  },

  {
    path: "/login",
    component: () => import("@/views/login/index.vue"),
    meta: { hidden: true },
  },

  {
    path: "/",
    name: "/",
    component: Layout,
    redirect: "/dashboard",
    children: [
      {
        path: "dashboard",
        component: () => import("@/views/dashboard/index.vue"),
        // 用于 keep-alive 功能，需要与 SFC 中自动推导或显式声明的组件名称一致
        // 参考文档: https://cn.vuejs.org/guide/built-ins/keep-alive.html#include-exclude
        name: "Dashboard",
        meta: {
          title: "dashboard",
          icon: "homepage",
          affix: true,
          keepAlive: true,
        },
      },
      {
        path: "401",
        component: () => import("@/views/error/401.vue"),
        meta: { hidden: true },
      },
      {
        path: "404",
        component: () => import("@/views/error/404.vue"),
        meta: { hidden: true },
      },
      {
        path: "profile",
        name: "Profile",
        component: () => import("@/views/profile/index.vue"),
        meta: { title: "个人中心", icon: "user", hidden: true },
      },
      {
        path: "my-notice",
        name: "MyNotice",
        component: () => import("@/views/profile/notice/index.vue"),
        meta: { title: "我的通知", icon: "user", hidden: true },
      },
      {
        path: "/detail/:id(\\d+)",
        name: "DemoDetail",
        component: () => import("@/views/demo/detail.vue"),
        meta: { title: "详情页缓存", icon: "user", hidden: true, keepAlive: true },
      },
    ],
  },

  // 产品模块静态路由（保证菜单未配好时也能跳转）
  {
    path: "/product",
    component: Layout,
    meta: { hidden: true },
    children: [
      {
        path: "productBom",
        name: "productBom",
        component: () => import("@/views/product/bom/index.vue"),
        meta: { title: "产品BOM管理" },
      },
      {
        path: "repair",
        name: "repair",
        component: () => import("@/views/product/repair/index.vue"),
        meta: { title: "返修管理" },
      },
      {
        path: "testRecord",
        name: "testRecord",
        component: () => import("@/views/product/testRecord/index.vue"),
        meta: { title: "测试记录表" },
      },
      {
        path: "warehouseLog",
        name: "warehouseLog",
        component: () => import("@/views/product/warehouseLog/index.vue"),
        meta: { title: "出入库记录" },
      },
      {
        path: "stockAlert",
        name: "stockAlert",
        component: () => import("@/views/product/stockAlert/index.vue"),
        meta: { title: "库存预警" },
      },
    ],
  },

  // 订单模块静态路由（保证菜单未配好时也能跳转）
  {
    path: "/order",
    component: Layout,
    meta: { hidden: true },
    children: [
      {
        path: "orderList",
        name: "orderList",
        component: () => import("@/views/order/index.vue"),
        meta: { title: "订单管理" },
      },
    ],
  },

  // 文件管理静态路由（保证菜单未配好时也能跳转）
  {
    path: "/file",
    component: Layout,
    meta: { hidden: true },
    children: [
      {
        path: "index",
        name: "FileManager",
        component: () => import("@/views/file/index.vue"),
        meta: { title: "文件管理" },
      },
    ],
  },

  // 审核管理静态路由（保证菜单未配好时也能跳转）
  {
    path: "/approval",
    component: Layout,
    meta: { hidden: true },
    children: [
      {
        path: "index",
        name: "ApprovalManager",
        component: () => import("@/views/approval/index.vue"),
        meta: { title: "审核管理" },
      },
      {
        path: "my-tasks",
        name: "MyApprovalTasks",
        component: () => import("@/views/approval/myTasks.vue"),
        meta: { title: "我的审批", hidden: true },
      },
      {
        path: "records",
        name: "ApprovalRecordsStatic",
        component: () => import("@/views/approval/records.vue"),
        meta: { title: "审批记录", hidden: true },
      },
    ],
  },
];

/**
 * 创建路由
 */
const router = createRouter({
  history: createWebHashHistory(),
  routes: constantRoutes,
  // 刷新时，滚动条位置还原
  scrollBehavior: () => ({ left: 0, top: 0 }),
});

// 全局注册 router
export function setupRouter(app: App<Element>) {
  app.use(router);
}

export default router;
