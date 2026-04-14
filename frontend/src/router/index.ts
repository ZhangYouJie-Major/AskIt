import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { authStorage } from '@/api/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/knowledge'
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/KnowledgeView.vue'),
    meta: { title: '知识库查询' }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { title: '管理后台' },
    children: [
      {
        path: '',
        redirect: '/admin/users'
      },
      {
        path: 'users',
        name: 'UserManage',
        component: () => import('@/views/UserManageView.vue'),
        meta: { title: '用户管理' }
      },
      {
        path: 'roles',
        name: 'RoleManage',
        component: () => import('@/views/RoleManageView.vue'),
        meta: { title: '角色管理' }
      },
      {
        path: 'departments',
        name: 'DepartmentManage',
        component: () => import('@/views/DepartmentManageView.vue'),
        meta: { title: '部门管理' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  if (to.path === '/admin/departments' && !authStorage.getUser()?.is_superuser) {
    next('/admin/users')
    return
  }

  document.title = `${to.meta.title || 'AskIt'} - 企业知识库`
  next()
})

export default router
