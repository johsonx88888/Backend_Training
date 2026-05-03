<script setup>
import { ref } from 'vue'
import Login from './components/Login.vue'
import ChatHeader from './components/ChatHeader.vue'
import MessageList from './components/MessageList.vue'
import ChatInput from './components/ChatInput.vue'
import { API_BASE } from './config.js'

// ===== 登录相关 =====
const savedUser = localStorage.getItem('chat_user_id')
const userId = ref(savedUser || '')
const isLoggedIn = ref(!!savedUser)

// ===== 状态区（所有数据放这里）=====
const messages = ref([
  { role: 'ai', content: '你好！我是 AI 助手，有什么可以帮你的？' }
])
const credits = ref(0)
const isLoading = ref(false)
const bgImage = ref('')
const inputText = ref('')

// ===== API 调用区（所有接口放这里）=====
async function loadHistory() {
  try {
    const res = await fetch(`${API_BASE}/history?user_id=${userId.value}&session_id=session001`)
    const data = await res.json()
    if (data.messages && data.messages.length > 0) {
      const formatted = data.messages.map(msg => ({
        ...msg,
        role: msg.role === 'assistant' ? 'ai' : msg.role
      }))
      messages.value = formatted.reverse()
    }
  } catch (e) {
    console.log('加载历史失败')
  }
}

async function fetchCredits() {
  try {
    const res = await fetch(`${API_BASE}/credits?user_id=${userId.value}`)
    const data = await res.json()
    credits.value = data.credits
  } catch (e) {
    console.log('查积分失败')
  }
}

async function sendMessage() {
  if (!inputText.value.trim()) return
  const userMessage = inputText.value
  messages.value.push({ role: 'user', content: userMessage })
  inputText.value = ''
  isLoading.value = true

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId.value,
        session_id: 'session001',
        message: userMessage
      })
    })
    const text = await response.text()
    messages.value.push({ role: 'ai', content: text })
  } catch (err) {
    messages.value.push({ role: 'ai', content: '连接失败:' + err.message })
  } finally {
    isLoading.value = false
    fetchCredits()
  }
}

async function clearHistory() {
  try {
    const res = await fetch(`${API_BASE}/chat/session?user_id=${userId.value}&session_id=session001`, {
      method: 'DELETE'
    })
    const data = await res.json()
    console.log(data.message)
    messages.value = [{ role: 'ai', content: '你好！我是 AI 助手，有什么可以帮你的？' }]
  } catch (e) {
    console.log('清空失败', e)
  }
}

// ===== 登录处理 =====
function handleLogin(name) {
  userId.value = name
  isLoggedIn.value = true
  loadHistory()
  fetchCredits()
}

// ===== 初始化 =====
if (isLoggedIn.value) {
  loadHistory()
  fetchCredits()
}

</script>


<template>
  <Login v-if="!isLoggedIn" @login="handleLogin" />
  <div v-else class="chat-box">
    <ChatHeader
      :credits="credits"
      @bg-change="bgImage = $event"
      @reset-bg="bgImage = ''"
      @clear-history="clearHistory"
    />
    <MessageList :messages="messages" :is-loading="isLoading" :bg-image="bgImage" />
    <ChatInput v-model="inputText" @send="sendMessage" />
  </div>
</template>


<style scoped>
.chat-box {
  max-width: 400px;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
  border: 1px solid #ddd;
}
</style>