/**
 * 权限管理 composable
 */
import { ref, computed } from 'vue'
import api from '@/api'
import { authStorage } from '@/api/auth'

// 权限类型
export type Permission = string

// 所有权限
export const ALL_PERMISSIONS: Permission[] = [
  'user:read',
  'user:write',
  'user:delete',
  'document:read',
  'document:write',
  'document:delete',
  'query:execute',
  'settings:read',
  'settings:write'
]

// 权限名称映射
export const PERMISSION_NAMES: Record<Permission, string> = {
  'user:read': '查看用户',
  'user:write': '创建/编辑用户',
  'user:delete': '删除用户',
  'document:read': '查看文档',
  'document:write': '上传/编辑文档',
  'document:delete': '删除文档',
  'query:execute': '发起问答',
  'settings:read': '查看配置',
  'settings:write': '修改配置'
}

// 单例状态
const permissions = ref<Permission[]>([])
const isSuperuser = ref(false)
const isLoaded = ref(false)

/**
 * 加载当前用户权限
 */
export async function loadUserPermissions() {
  const user = authStorage.getUser()
  if (!user) {
    permissions.value = []
    isSuperuser.value = false
    isLoaded.value = true
    return
  }

  try {
    const response = await api.get<any, { permissions: Permission[]; is_superuser: boolean }>('/permissions/my')
    permissions.value = response.permissions
    isSuperuser.value = response.is_superuser
    console.log('[Permission] Loaded permissions:', response.permissions, 'isSuperuser:', response.is_superuser)
  } catch (error) {
    console.error('[Permission] Failed to load permissions:', error)
    permissions.value = []
    isSuperuser.value = false
  } finally {
    isLoaded.value = true
  }
}

/**
 * 检查是否拥有指定权限
 */
export function hasPermission(permission: Permission): boolean {
  if (isSuperuser.value) return true
  return permissions.value.includes(permission)
}

/**
 * 检查是否拥有所有指定权限
 */
export function hasAllPermissions(requiredPermissions: Permission[]): boolean {
  if (isSuperuser.value) return true
  return requiredPermissions.every(p => permissions.value.includes(p))
}

/**
 * 检查是否拥有任一指定权限
 */
export function hasAnyPermission(requiredPermissions: Permission[]): boolean {
  if (isSuperuser.value) return true
  return requiredPermissions.some(p => permissions.value.includes(p))
}

/**
 * 清除权限状态（退出登录时调用）
 */
export function clearPermissions() {
  permissions.value = []
  isSuperuser.value = false
  isLoaded.value = false
}

/**
 * 使用权限 composable
 */
export function usePermission() {
  return {
    permissions: computed(() => permissions.value),
    isSuperuser: computed(() => isSuperuser.value),
    isLoaded: computed(() => isLoaded.value),
    hasPermission,
    hasAllPermissions,
    hasAnyPermission,
    loadUserPermissions,
    clearPermissions
  }
}
