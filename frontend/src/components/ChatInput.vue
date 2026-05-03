<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'send'])

// 这是关键！让 v-model 能跨组件工作
const inputText = computed({
  get: () => props.modelValue,           // 读：从爸爸那拿
  set: (val) => emit('update:modelValue', val)  // 写：通知爸爸更新
})

function onSend() {
  if (!inputText.value.trim()) return
  emit('send')
}
</script>

<template>
  <div class="input-area">
    <input v-model="inputText" @keyup.enter="onSend" placeholder="输入消息，按回车发送..." />
    <button @click="onSend">发送</button>
  </div>
</template>

<style scoped>
.input-area {
  display: flex;
  padding: 15px;
  background: white;
  border-top: 1px solid #ddd;
}

.input-area input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  margin-right: 10px;
}

.input-area button {
  padding: 10px 20px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.input-area button:hover {
  background: #369870;
}
</style>