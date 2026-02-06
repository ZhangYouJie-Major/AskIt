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
          <el-button v-if="!isLoggedIn" @click="loginDialogVisible = true" type="primary">登录</el-button>
          <div v-else class="user-info">
            <el-dropdown>
              <span class="user-name">
                <el-icon><User /></el-icon>
                {{ username }}
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </el-header>

    <!-- 登录对话框 -->
    <el-dialog v-model="loginDialogVisible" title="登录" width="400px">
      <el-form :model="loginForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="loginForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="loginDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleLogin" :loading="loginLoading">登录</el-button>
      </template>
    </el-dialog>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const currentRoute = computed(() => route.path)

// 登录状态
const isLoggedIn = ref(false)
const username = ref('')
const loginDialogVisible = ref(false)
const loginLoading = ref(false)

const loginForm = ref({
  username: '',
  password: ''
})

// 处理登录
const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loginLoading.value = true
  try {
    // TODO: 调用登录 API
    // 模拟登录成功
    await new Promise(resolve => setTimeout(resolve, 500))
    isLoggedIn.value = true
    username.value = loginForm.value.username
    loginDialogVisible.value = false
    ElMessage.success('登录成功')
  } catch (error: any) {
    ElMessage.error(error.message || '登录失败')
  } finally {
    loginLoading.value = false
  }
}

// 处理退出登录
const handleLogout = () => {
  isLoggedIn.value = false
  username.value = ''
  ElMessage.success('已退出登录')
}
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
