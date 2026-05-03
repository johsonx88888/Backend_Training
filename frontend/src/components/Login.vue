<script setup>
import { ref } from 'vue'

const emit = defineEmits(['login'])

const username = ref('')

function onLogin() {
  const name = username.value.trim()
  if (!name) {
    alert('请输入用户名！')
    return
  }
  // 存到浏览器本地，刷新也不会丢
  localStorage.setItem('chat_user_id', name)
  emit('login', name)
}
</script>

<template>
  <div class="login-box">
    <h2>🤖 AI 聊天助手</h2>
    <p>请输入你的用户名开始对话</p>
    <input
      v-model="username"
      @keyup.enter="onLogin"
      placeholder="例如：zhangsan"
    />
    <button @click="onLogin">进入聊天</button>
  </div>
</template>

<style scoped>
.login-box {
  max-width: 400px;
  margin: 100px auto;
  padding: 40px;
  text-align: center;
  border: 1px solid #ddd;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.login-box h2 {
  color: #42b983;
  margin-bottom: 10px;
}

.login-box p {
  color: #666;
  margin-bottom: 20px;
}

.login-box input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 5px;
  margin-bottom: 15px;
  font-size: 16px;
  box-sizing: border-box;
}

.login-box button {
  width: 100%;
  padding: 12px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
}

.login-box button:hover {
  background: #369870;
}
</style>
