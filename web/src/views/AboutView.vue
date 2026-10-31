<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const health = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    health.value = await api.health()
  } catch (err) {
    error.value = err.message
  }
})
</script>

<template>
  <section>
    <div class="page-head">
      <h1>关于</h1>
      <p>离线演示用的内容社区 + 个性化推荐系统。</p>
    </div>

    <article class="card" style="padding: 22px">
      <p>版本：<code>0.1.0</code>（界面与后端同版本号，桌面打包见 <code>desktop/version_info.txt</code>）</p>
      <p v-if="error" class="error">{{ error }}</p>
      <template v-else-if="health">
        <p>后端版本：<code>{{ health.version }}</code></p>
        <p>模型版本：<code>{{ health.model_version }}</code></p>
        <p>
          数据规模：商品 {{ health.items }} · 用户 {{ health.users }} · 行为 {{ health.events }}
          · 安利 {{ health.posts }}
        </p>
        <p v-if="health.demo_data" class="notice" style="margin: 12px 0 0">
          当前使用确定性生成的<strong>演示数据</strong>，封面为程序生成的示意插画，指标不代表真实业务效果。
        </p>
        <p class="meta">服务状态：{{ health.status }}</p>
      </template>
      <p v-else class="meta">读取服务信息中…</p>
    </article>

    <article class="card section" style="padding: 22px">
      <h2 style="margin-top: 0">推荐口径</h2>
      <ul>
        <li>召回：物品协同过滤 + TF-IDF 内容相似 + 时间衰减热门 + 搜索关键词 + 安利停留时长。</li>
        <li>融合：五路归一化后按权重加权，权重在 <code>backend/config/rec.yaml</code>。</li>
        <li>重排：MMR 去冗余 + 单类目占比上限，已购商品直接过滤。</li>
        <li>评估：<code>python -m eval.run_eval</code> 输出 Recall@K / NDCG@K / 覆盖率 / 新颖度。</li>
      </ul>
    </article>
  </section>
</template>
