<script setup>
import {ref} from 'vue'

// ===== 接收父组件传进来的积分 =====
const props = defineProps({
    credits:{type:Number,default:0}
})

//===== 定义要通知父组件的事件 =====
const emit=defineEmits(['bg-change','reset-bg','clear-history'])

//===== 换背景相关 =====
const fileInput = ref(null)

function triggerFileInput(){
    fileInput.value.click()
}

function handleFileChange(e) {
     const file = e.target.files[0]
     if (!file) return
     const reader = new FileReader()
     reader.onload = (event) => {
        emit('bg-change', event.target.result)  // 把图片 URL 传给父组件
         }
  reader.readAsDataURL(file)
}

// ===== 恢复默认背景 =====
function onResetBg() {
  emit('reset-bg')
}

// ===== 清空历史 =====
async function onClearHistory() {
  if (!confirm('确定要清空当前会话的所有历史记录吗？')) return
  emit('clear-history')
}
</script>


<template>
  <div class="header">
    AI 聊天助手
    <span class="credits">积分：{{ credits }}</span>
    <button @click="triggerFileInput" class="bg-btn">🖼️ 换背景</button>
    <button @click="onResetBg" class="bg-btn">↩️ 默认背景</button>
    <button @click="onClearHistory" class="bg-btn">🗑️ 清空</button>
    <input
      type="file"
      accept="image/*"
      ref="fileInput"
      @change="handleFileChange"
      style="display: none"
    />
  </div>
</template>

<style scoped>
.header {
  background: #42b96aff;
  color: white;
  padding: 15px;
  text-align: center;
  font-size: 18px;
  font-weight: bold;
}
.credits {
  font-size: 14px;
  margin-left: 10px;
  opacity: 0.9;
}
.bg-btn {
  background: rgba(255, 255, 255, 0.3);
  border: none;
  color: white;
  padding: 5px 10px;
  border-radius: 5px;
  cursor: pointer;
  margin-left: 10px;
  font-size: 14px;
}
.bg-btn:hover {
  background: rgba(255, 255, 255, 0.5);
}
</style>