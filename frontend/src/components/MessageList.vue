<script setup>
// 只接收数据，不发出任何事件
const props = defineProps({
  messages: { type: Array, default: () => [] },
  isLoading: { type: Boolean, default: false },
  bgImage: { type: String, default: '' }
})
</script>

<template>
  <div class="messages" :style="bgImage ? { backgroundImage: `url(${bgImage})` } : {}">
    <div v-for="(msg, index) in messages" :key="index" :class="['msg', msg.role]">
      {{ msg.content }}
    </div>
    <div v-if="isLoading" class="msg ai loading">AI正在思考...</div>
  </div>
</template>

<style scoped>
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f5f5;
}

.msg {
  margin: 10px 0;
  padding: 10px 15px;
  border-radius: 10px;
  max-width: 70%;
  width: fit-content;
  word-wrap: break-word;
}

.msg.ai {
  background: rgba(255, 255, 255, 0.9);
  align-self: flex-start;
}

.msg.ai.loading {
  background: linear-gradient(90deg, #42b983, #999, #42b983);
  background-size: 200% auto;
  color: transparent;
  -webkit-background-clip: text;
  background-clip: text;
  animation: shine 2s linear infinite;
}

@keyframes shine {
  to {
    background-position: 200% center;
  }
}

.msg.user {
  background: rgba(66, 185, 131, 0.9);
  color: white;
  margin-left: auto;
}
</style>