<template>
  <div class="login-page">
    <div class="login-page__bg">
      <div class="login-page__bg-circle login-page__bg-circle--1"></div>
      <div class="login-page__bg-circle login-page__bg-circle--2"></div>
      <div class="login-page__bg-circle login-page__bg-circle--3"></div>
    </div>
    <div class="login-page__content">
      <div class="login-card">
        <div class="login-card__header">
          <svg class="login-card__logo" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="8" fill="#1677FF"/>
            <path d="M8 10L16 16L24 10" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <rect x="7" y="10" width="18" height="12" rx="2" stroke="white" stroke-width="2"/>
          </svg>
          <h1 class="login-card__title">CronMail</h1>
          <p class="login-card__subtitle">邮件定时发送管理系统</p>
        </div>
        <el-form ref="formRef" :model="form" :rules="rules" class="login-card__form" @keyup.enter="handleLogin">
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="请输入用户名" size="large" :prefix-icon="User">
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" show-password :prefix-icon="Lock">
            </el-input>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" :loading="loading" class="login-card__submit" @click="handleLogin">
              登 录
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const handleLogin = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.login(form)
    ElMessage.success('登录成功')
    router.push('/')
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;

  &__bg {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }

  &__bg-circle {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.05);

    &--1 {
      width: 600px;
      height: 600px;
      top: -200px;
      right: -100px;
    }

    &--2 {
      width: 400px;
      height: 400px;
      bottom: -150px;
      left: -100px;
    }

    &--3 {
      width: 300px;
      height: 300px;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
    }
  }

  &__content {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 420px;
    padding: var(--spacing-xl);
  }
}

.login-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  padding: var(--spacing-3xl);

  &__header {
    text-align: center;
    margin-bottom: var(--spacing-2xl);
  }

  &__logo {
    width: 56px;
    height: 56px;
    margin-bottom: var(--spacing-base);
  }

  &__title {
    font-size: var(--font-size-2xl);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-xs);
  }

  &__subtitle {
    font-size: var(--font-size-base);
    color: var(--color-text-tertiary);
  }

  &__form {
    .el-form-item {
      margin-bottom: var(--spacing-xl);
    }
  }

  &__submit {
    width: 100%;
    height: 44px;
    font-size: var(--font-size-md);
    font-weight: var(--font-weight-semibold);
    border-radius: var(--radius-md);
  }
}
</style>