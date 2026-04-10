<template>
  <div class="role-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>角色管理</span>
          <el-button v-if="hasPermission('user:write')" type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建角色
          </el-button>
        </div>
      </template>

      <el-table :data="roles" v-loading="loading" stripe>
        <el-table-column prop="name" label="角色名" width="150" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="权限数量" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.permission_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="用户数" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.user_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button v-if="hasPermission('user:write')" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="hasPermission('user:write')" size="small" @click="handleConfigPermissions(row)">
              配置权限
            </el-button>
            <el-button
              v-if="hasPermission('user:delete')"
              size="small"
              type="danger"
              @click="handleDelete(row)"
              :disabled="row.user_count > 0"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑角色对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建角色' : '编辑角色'"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="角色名" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
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

    <!-- 配置权限抽屉 -->
    <el-drawer v-model="permissionsDrawerVisible" title="配置权限" size="500px">
      <div class="permissions-config">
        <el-checkbox
          v-for="perm in allPermissions"
          :key="perm.id"
          v-model="selectedPermissionIds"
          :label="perm.id"
          style="display: block; margin-bottom: 12px"
        >
          <strong>{{ perm.name }}</strong>
          <span class="perm-code">{{ perm.code }}</span>
          <span class="perm-desc">{{ perm.description }}</span>
        </el-checkbox>
      </div>
      <template #footer>
        <el-button @click="permissionsDrawerVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitPermissions" :loading="submitting">
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
import { rolesApi, permissionsApi } from '@/api/rbac'
import { usePermission } from '@/composables/usePermission'

const { hasPermission } = usePermission()

const roles = ref<any[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const submitting = ref(false)
const editingRoleId = ref<number | null>(null)

const form = reactive({
  name: '',
  description: '',
  is_active: true
})

const permissionsDrawerVisible = ref(false)
const allPermissions = ref<any[]>([])
const selectedPermissionIds = ref<number[]>([])
const currentRoleId = ref<number | null>(null)

const loadRoles = async () => {
  loading.value = true
  try {
    roles.value = await rolesApi.list()
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogMode.value = 'create'
  editingRoleId.value = null
  Object.assign(form, { name: '', description: '', is_active: true })
  dialogVisible.value = true
}

const handleEdit = async (row: any) => {
  dialogMode.value = 'edit'
  editingRoleId.value = row.id
  try {
    const role = await rolesApi.getById(row.id)
    Object.assign(form, {
      name: role.name,
      description: role.description,
      is_active: role.is_active
    })
    dialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  }
}

const handleSubmit = async () => {
  if (!form.name) {
    ElMessage.warning('请填写角色名')
    return
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await rolesApi.create({
        name: form.name,
        description: form.description || undefined,
        permission_ids: []
      })
      ElMessage.success('创建成功')
    } else {
      await rolesApi.update(editingRoleId.value!, {
        name: form.name,
        description: form.description || undefined,
        is_active: form.is_active
      })
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadRoles()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定删除该角色吗？', '提示', { type: 'warning' })
    await rolesApi.delete(row.id)
    ElMessage.success('删除成功')
    loadRoles()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleConfigPermissions = async (row: any) => {
  currentRoleId.value = row.id
  // 加载所有权限
  if (allPermissions.value.length === 0) {
    allPermissions.value = await permissionsApi.list()
  }
  // 加载角色当前权限
  try {
    const role = await rolesApi.getById(row.id)
    selectedPermissionIds.value = role.permissions.map((p: any) => p.id)
  } catch (error: any) {
    selectedPermissionIds.value = []
  }
  permissionsDrawerVisible.value = true
}

const handleSubmitPermissions = async () => {
  if (!currentRoleId.value) return
  submitting.value = true
  try {
    await rolesApi.updatePermissions(currentRoleId.value, {
      permission_ids: selectedPermissionIds.value
    })
    ElMessage.success('权限配置成功')
    permissionsDrawerVisible.value = false
    loadRoles()
  } catch (error: any) {
    ElMessage.error(error.message || '配置失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadRoles()
})
</script>

<style scoped>
.role-manage {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.perm-code {
  display: block;
  color: #409eff;
  font-size: 12px;
  font-family: monospace;
}

.perm-desc {
  display: block;
  color: #909399;
  font-size: 12px;
}
</style>
