<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <div class="logo">
          <el-icon :size="28"><ChatLineSquare /></el-icon>
          <span>AskIt</span>
        </div>
        <el-menu
          :default-active="currentRoute"
          mode="horizontal"
          router
          class="header-menu"
        >
          <el-menu-item index="/knowledge">知识库</el-menu-item>
          <el-menu-item index="/admin">管理后台</el-menu-item>
        </el-menu>
        <div class="header-actions">
          <el-button>登录</el-button>
        </div>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentRoute = computed(() => route.path)
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0;
  height: 60px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.header-content {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 24px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 600;
  color: #409eff;
  margin-right: 48px;
}

.header-menu {
  flex: 1;
  border-bottom: none;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
  padding: 24px;
}
</style>
