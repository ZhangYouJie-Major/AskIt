<template>
  <div class="department-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>部门管理</span>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建部门
          </el-button>
        </div>
      </template>

      <el-table :data="departments" v-loading="loading" stripe>
        <el-table-column prop="name" label="部门名称" min-width="180" />
        <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
        <el-table-column label="用户数" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.user_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button
              size="small"
              :type="row.is_active ? 'warning' : 'success'"
              @click="handleToggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建部门' : '编辑部门'"
      width="500px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="部门名称" required>
          <el-input v-model="form.name" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { departmentsApi, type Department } from '@/api/departments'

const departments = ref<Department[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const submitting = ref(false)
const editingDepartmentId = ref<number | null>(null)

const form = reactive({
  name: '',
  description: ''
})

const loadDepartments = async () => {
  loading.value = true
  try {
    departments.value = await departmentsApi.list()
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  Object.assign(form, {
    name: '',
    description: ''
  })
}

const handleCreate = () => {
  dialogMode.value = 'create'
  editingDepartmentId.value = null
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row: Department) => {
  dialogMode.value = 'edit'
  editingDepartmentId.value = row.id
  Object.assign(form, {
    name: row.name,
    description: row.description || ''
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const name = form.name.trim()
  const description = form.description.trim()

  if (!name) {
    ElMessage.warning('请填写部门名称')
    return
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await departmentsApi.create({
        name,
        description: description || undefined
      })
      ElMessage.success('创建成功')
    } else if (editingDepartmentId.value !== null) {
      await departmentsApi.update(editingDepartmentId.value, {
        name,
        description: description || undefined
      })
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    await loadDepartments()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleToggleStatus = async (row: Department) => {
  const nextStatus = !row.is_active
  const actionText = nextStatus ? '启用' : '禁用'

  try {
    await ElMessageBox.confirm(`确定${actionText}该部门吗？`, '提示', {
      type: 'warning'
    })
    await departmentsApi.updateStatus(row.id, {
      is_active: nextStatus
    })
    ElMessage.success(`${actionText}成功`)
    await loadDepartments()
  } catch (error: any) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.message || `${actionText}失败`)
    }
  }
}

onMounted(() => {
  loadDepartments()
})
</script>

<style scoped>
.department-manage {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
