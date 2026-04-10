<template>
  <div class="user-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button v-if="hasPermission('user:write')" type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建用户
          </el-button>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="department_name" label="部门" width="120" />
        <el-table-column label="角色" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="role in row.roles"
              :key="role.id"
              size="small"
              class="role-tag"
            >
              {{ role.name }}
            </el-tag>
            <span v-if="!row.roles || row.roles.length === 0" class="no-role">
              未分配角色
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后登录" width="180">
          <template #default="{ row }">
            {{ formatDate(row.last_login) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-if="hasPermission('user:write')" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="hasPermission('user:write')" size="small" @click="handleAssignRoles(row)">分配角色</el-button>
            <el-button v-if="hasPermission('user:delete')" size="small" type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: center"
        @current-change="loadUsers"
        @size-change="loadUsers"
      />
    </el-card>

    <!-- 新建/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建用户' : '编辑用户'"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="dialogMode === 'edit'" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="form.email" type="email" />
        </el-form-item>
        <el-form-item label="密码" :required="dialogMode === 'create'">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="form.department_id" placeholder="选择部门">
            <el-option label="无" :value="null" />
            <el-option
              v-for="dept in departments"
              :key="dept.id"
              :label="dept.name"
              :value="dept.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 分配角色抽屉 -->
    <el-drawer v-model="rolesDrawerVisible" title="分配角色" size="400px">
      <div class="roles-assign">
        <el-checkbox-group v-model="selectedRoleIds">
          <el-checkbox
            v-for="role in allRoles"
            :key="role.id"
            :label="role.id"
            style="display: block; margin-bottom: 12px"
          >
            {{ role.name }}
            <span class="role-desc">{{ role.description }}</span>
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="rolesDrawerVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitRoles" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { rolesApi, userRolesApi } from '@/api/rbac'
import api from '@/api'
import { usePermission } from '@/composables/usePermission'

const { hasPermission } = usePermission()

const users = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const departments = ref<any[]>([])

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const submitting = ref(false)
const editingUserId = ref<number | null>(null)

const rolesDrawerVisible = ref(false)
const allRoles = ref<any[]>([])
const selectedRoleIds = ref<number[]>([])
const currentUserId = ref<number | null>(null)

const form = reactive({
  username: '',
  email: '',
  password: '',
  full_name: '',
  department_id: null as number | null,
  is_active: true
})

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await api.get('/users/', {
      params: { skip: (currentPage.value - 1) * pageSize.value, limit: pageSize.value }
    })
    users.value = Array.isArray(response) ? response : []
    total.value = users.value.length
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogMode.value = 'create'
  editingUserId.value = null
  Object.assign(form, {
    username: '',
    email: '',
    password: '',
    full_name: '',
    department_id: null,
    is_active: true
  })
  dialogVisible.value = true
}

const handleEdit = (row: any) => {
  dialogMode.value = 'edit'
  editingUserId.value = row.id
  Object.assign(form, {
    username: row.username,
    email: row.email,
    password: '',
    full_name: row.full_name,
    department_id: row.department_id,
    is_active: row.is_active
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.username || !form.email) {
    ElMessage.warning('请填写必填项')
    return
  }
  if (dialogMode.value === 'create' && !form.password) {
    ElMessage.warning('请填写密码')
    return
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await api.post('/users/', form)
      ElMessage.success('创建成功')
    } else {
      const data = { ...form }
      if (!data.password) delete data.password
      await api.put(`/users/${editingUserId.value}`, data)
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定删除该用户吗？', '提示', { type: 'warning' })
    await api.delete(`/users/${row.id}`)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleAssignRoles = async (row: any) => {
  currentUserId.value = row.id
  // 加载所有角色
  if (allRoles.value.length === 0) {
    allRoles.value = await rolesApi.list()
  }
  // 加载用户当前角色
  const userRoles = await userRolesApi.getUserRoles(row.id)
  selectedRoleIds.value = userRoles.map((r: any) => r.id)
  rolesDrawerVisible.value = true
}

const handleSubmitRoles = async () => {
  if (!currentUserId.value) return
  submitting.value = true
  try {
    await userRolesApi.assign(currentUserId.value, { role_ids: selectedRoleIds.value })
    ElMessage.success('角色分配成功')
    rolesDrawerVisible.value = false
    loadUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '分配失败')
  } finally {
    submitting.value = false
  }
}

const formatDate = (date: string | null) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.user-manage {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.role-tag {
  margin-right: 4px;
}

.no-role {
  color: #909399;
  font-size: 12px;
}

.role-desc {
  display: block;
  color: #909399;
  font-size: 12px;
  margin-top: 2px;
}
</style>
