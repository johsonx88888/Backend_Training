<script setup>
import { ref } from 'vue'

// 消息列表：每个消息有 role（谁发的）和 content（内容）
const messages = ref([
  { role: 'ai', content: '你好！我是 AI 助手，有什么可以帮你的？' }
])

//ai思考状态
const isLoading=ref(false)

//背景图片更换
const bgImage=ref('')
const fileInput=ref(null) //文件选择器引用

function triggerFileInput(){
  fileInput.value.click()  //点击按钮触发文件选择器
}

function handleFileChange(e){
  const file=e.target.files[0]
  if(!file) return

  //把图片文件转成URL
  const reader=new FileReader()
  reader.onload=(event)=>{
    bgImage.value=event.target.result
  }
  reader.readAsDataURL(file)
}

//恢复默认背景设置
function resetBg(){
  bgImage.value=''
}

// 输入框的内容
const inputText = ref('')

// 发送消息的函数
async function sendMessage(){
  if(!inputText.value.trim()) return

  //1、显示用户消息
  const userMessage=inputText.value
  messages.value.push({role:'user',content:userMessage})
  
  //清空输入框
  inputText.value = '' 

  //ai思考加载状态拨正
  isLoading.value=true

  //2、调用后端/chat接口
  try{
    const response=await fetch('http://localhost:8000/chat',{
      method: 'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        user_id:'user001',
        session_id:'session001',
        message:userMessage
      })
    })
    
    //3、获取AI回复
    const text=await response.text()

    //4、显示AI回复
    messages.value.push({role:'ai',content:text})
  }catch(err){
    messages.value.push({role:'ai',content:'连接失败:'+err.message})
  }finally{
    isLoading.value=false
  }
}

</script>



<template>
  <div class="chat-box">
    <!-- 顶部标题 -->
    <div class="header">AI 聊天助手
     <button @click="triggerFileInput" class="bg-btn">🖼️ 换背景</button>
     <button @click="resetBg" class="bg-btn"> ↩️ 默认</button>
     <input 
    type="file" 
    accept="image/*" 
    ref="fileInput"
    @change="handleFileChange"
    style="display: none"
  />
    </div>
    <!-- 消息展示区 -->
    <div class="messages" :style="bgImage ? { backgroundImage: `url(${bgImage})`, backgroundSize: 'cover' } : {}">
      <div 
        v-for="(msg, index) in messages" 
        :key="index" 
        :class="['msg', msg.role]"
      >
        {{ msg.content }}
      </div>
      <!--加载提示-->
      <div v-if="isLoading" class="msg ai loading">AI正在思考...</div>
    </div>
    
    <!-- 底部输入区 -->
    <div class="input-area">
      <input 
        v-model="inputText" 
        @keyup.enter="sendMessage"
        placeholder="输入消息，按回车发送..." 
      />
      <button @click="sendMessage">发送</button>
    </div>
  </div>
</template>



<style scoped>

/* 整个聊天框 */
.chat-box {
  max-width: 400px; 
  margin: 0 auto ;  
  height: 100vh; 
  display: flex;  
  flex-direction: column;
  border: 1px solid #ddd;
}

/* 顶部标题 */
.header {
  background: #42b96aff;
  color: white;
  padding: 15px;
  text-align: center;
  font-size: 18px;
  font-weight:bold;
}

/* 消息区域 */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f5f5;
}

/* 每条消息的样式 */
.msg {
  margin: 10px 0;
  padding: 10px 15px;
  border-radius: 10px;
  max-width: 70%;
  width:fit-content;
  word-wrap: break-word;
}

/* AI 消息：左边，白色 */
.msg.ai {
  background: rgba(255,255,255,0.9);
  align-self: flex-start;
}

/* ai思考时的气泡样式 */
.msg.ai.loading{
  background:linear-gradient(90deg,#42b983,#999, #42b983);
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


/* 用户消息：右边，绿色 */
.msg.user {
  background:rgba(66,185,131,0.9);
  color: white;
  margin-left: auto;
}

/* 输入区域 */
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

.bg-btn {
  background: rgba(255,255,255,0.3);
  border: none;
  color: white;
  padding: 5px 10px;
  border-radius: 5px;
  cursor: pointer;
  margin-left: 10px;
  font-size: 14px;
}
.bg-btn:hover {
  background: rgba(255,255,255,0.5);
}

</style>

