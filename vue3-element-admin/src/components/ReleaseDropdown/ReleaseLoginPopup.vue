<template>
  <ReleaseDetailDialog
    v-model="loginPopupVisible"
    :detail="loginPopupDetail"
    confirm-text="我知道了"
    @confirm="dismissLoginPopup"
  />
</template>

<script setup lang="ts">
import ReleaseDetailDialog from "./ReleaseDetailDialog.vue";
import { useReleaseLoginPopup } from "./useReleaseLoginPopup";

const { loginPopupVisible, loginPopupDetail, checkAndShowLoginPopup, dismissLoginPopup } =
  useReleaseLoginPopup();

onMounted(() => {
  checkAndShowLoginPopup();
});
</script>
