<template>
  <!-- key=fullPath：同组件不同参数的路由（如 /doc/check → /doc/transfer）强制重挂载，
       避免 DocSheet 等页面在 setup 里一次性读取 route.params 后不随路由更新的旧状态残留 -->
  <router-view :key="$route.fullPath" />
</template>

<script setup>
</script>

<style>
html, body, #app { height: 100%; margin: 0; }
body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f0f2f5; }
</style>
