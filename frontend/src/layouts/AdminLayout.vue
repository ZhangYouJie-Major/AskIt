<template>
  <el-container class="admin-layout">
    <!-- 侧边栏 -->
    <el-aside width="200px" class="admin-sidebar">
      <el-menu
        :default-active="currentRoute"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/roles">
          <el-icon><Key /></el-icon>
          <span>角色管理</span>
        </el-menu-item>
        <el-menu-item v-if="isSuperuser" index="/admin/departments">
          <el-icon><OfficeBuilding /></el-icon>
          <span>部门管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="admin-main">
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { User, Key, OfficeBuilding } from '@element-plus/icons-vue'
import { authStorage } from '@/api/auth'

const route = useRoute()
const currentRoute = computed(() => route.path)
const isSuperuser = computed(() => authStorage.getUser()?.is_superuser === true)
</script>

<style scoped>
.admin-layout {
  height: 100%;
}

.admin-sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  padding-top: 8px;
}

.sidebar-menu {
  border-right: none;
}

.admin-main {
  background: #f5f7fa;
}
</style>
