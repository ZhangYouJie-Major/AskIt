<template>
  <div class="knowledge-view">
    <el-card class="query-card">
      <template #header>
        <div class="card-header">
          <span>🔍 智能问答</span>
        </div>
      </template>

      <el-form @submit.prevent="handleQuery">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          placeholder="请输入您的问题..."
          :disabled="loading"
        />
        <div class="form-actions">
          <el-button
            type="primary"
            @click="handleQuery"
            :loading="loading"
            :disabled="!question.trim()"
          >
            提问
          </el-button>
          <el-button @click="handleClear">清空</el-button>
        </div>
      </el-form>

      <!-- 消息列表 -->
      <div v-if="messages.length > 0" class="messages">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', msg.role]"
        >
          <div class="message-avatar">
            <el-icon v-if="msg.role === 'user'"><User /></el-icon>
            <el-icon v-else><Robot /></el-icon>
          </div>
          <div class="message-content">
            <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="msg.sources && msg.sources.length > 0" class="message-sources">
              <el-tag
                v-for="(source, i) in msg.sources"
                :key="i"
                size="small"
                type="info"
              >
                {{ source.filename }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { queryApi } from '@/api/modules'

const question = ref('')
const loading = ref(false)
const messages = ref<Array<{
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}>>([])

const handleQuery = async () => {
  if (!question.value.trim()) return

  const userMessage = question.value
  messages.value.push({
    role: 'user',
    content: userMessage
  })

  question.value = ''
  loading.value = true

  try {
    const response = await queryApi.query({
      question: userMessage,
      department_id: 1, // TODO: 从用户信息获取
      history: messages.value
        .filter(m => m.role === 'user')
        .map(m => ({ role: m.role, content: m.content })),
      top_k: 5
    })

    messages.value.push({
      role: 'assistant',
      content: response.answer,
      sources: response.sources
    })
  } catch (error: any) {
    ElMessage.error(error.message || '查询失败')
    messages.value.pop()
  } finally {
    loading.value = false
  }
}

const handleClear = () => {
  messages.value = []
  question.value = ''
}

const renderMarkdown = (text: string) => {
  // 简单的 markdown 渲染
  return text
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
}
</script>

<style scoped>
.knowledge-view {
  max-width: 1000px;
  margin: 0 auto;
}

.query-card {
  min-height: 600px;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
}

.form-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}

.messages {
  margin-top: 24px;
  border-top: 1px solid #e4e7ed;
  padding-top: 24px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #409eff;
  color: #fff;
}

.message-content {
  max-width: 70%;
}

.message.user .message-content {
  text-align: left;
}

.message-text {
  padding: 12px 16px;
  border-radius: 8px;
  background: #f5f7fa;
  line-height: 1.6;
}

.message.user .message-text {
  background: #409eff;
  color: #fff;
}

.message-sources {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
