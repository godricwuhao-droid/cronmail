import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getUserInfo } from '@/api/auth'

interface UserInfo {
  id: string
  username: string
  email: string
  name: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<UserInfo | null>(null)

  const setToken = (t: string) => {
    token.value = t
    localStorage.setItem('token', t)
  }

  const setUser = (u: UserInfo) => {
    user.value = u
    localStorage.setItem('user', JSON.stringify(u))
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const login = async (data: { username: string; password: string }) => {
    const res = await loginApi(data)
    setToken(res.access_token)
    const userInfo = await getUserInfo()
    setUser(userInfo)
  }

  return { token, user, setToken, setUser, logout, login }
})