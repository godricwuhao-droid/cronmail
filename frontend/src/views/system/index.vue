<script setup lang="ts">
/**
 * 系统配置 - 父布局壳
 *
 * 该组件作为 `/system` 路径的父路由组件，
 * 实际内容由子路由（smtp / colleagues）通过 router-view 渲染。
 *
 * 注：早期版本此处直接渲染占位内容，已重构为标准嵌套路由。
 */
</script>

<template>
  <router-view />
</template>
