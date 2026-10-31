<script setup>
import { useShopStore } from '../stores/shop'

const shop = useShopStore()
</script>

<template>
  <section>
    <div class="page-head"><h1>钱包</h1><p>优惠券、积分、红包和余额都在这里。</p></div>

    <div class="stat-grid" style="margin-bottom: 18px">
      <div class="stat">
        <b>{{ shop.wallet.balance }}</b>
        <span>余额（元）</span>
      </div>
      <div class="stat">
        <b>{{ shop.wallet.coupons }}</b>
        <span>优惠券</span>
      </div>
      <div class="stat">
        <b>{{ shop.wallet.points }}</b>
        <span>积分</span>
      </div>
      <div class="stat">
        <b>{{ shop.wallet.red_packets }}</b>
        <span>红包</span>
      </div>
    </div>

    <div class="section-card">
      <div class="section-head" style="margin-bottom: 12px"><h2>可用优惠</h2></div>
      <div class="row-list">
        <div class="row-item">
          <span class="tag">满 199 减 20</span>
          <div class="grow meta">全场通用 · 有效期至 2026-12-31</div>
          <span class="status-pill">可用</span>
        </div>
        <div class="row-item">
          <span class="tag">满 99 减 10</span>
          <div class="grow meta">食品饮料类目 · 有效期至 2026-11-30</div>
          <span class="status-pill">可用</span>
        </div>
        <div class="row-item">
          <span class="tag">新人红包 ¥5</span>
          <div class="grow meta">无门槛 · 下单自动抵扣</div>
          <span class="status-pill">可用</span>
        </div>
      </div>
    </div>

    <div class="section-card">
      <div class="section-head" style="margin-bottom: 12px"><h2>积分规则</h2></div>
      <p class="meta" style="margin: 0">
        每支付 1 元累计 1 积分（演示环境每单 +10），积分可在结算时抵扣，100 积分 = 1 元。
      </p>
    </div>
  </section>
</template>
