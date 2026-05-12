<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { useData } from 'vitepress'

const props = defineProps<{
  code: string
}>()

const { isDark } = useData()
const svg = ref('')
const error = ref<string | null>(null)

function decodeDiagram(value: string): string {
  const binary = window.atob(value)
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

async function renderDiagram(): Promise<void> {
  await nextTick()

  try {
    const diagram = decodeDiagram(props.code)
    const mermaid = (await import('mermaid')).default
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: isDark.value ? 'dark' : 'base',
      flowchart: {
        nodeSpacing: 40,
        rankSpacing: 50,
        useMaxWidth: true,
      },
      themeVariables: {
        primaryColor: isDark.value ? '#2f1f1b' : '#fff5f2',
        primaryTextColor: isDark.value ? '#f8f8f8' : '#1f1f1f',
        primaryBorderColor: '#ed4b2f',
        fontSize: '13px',
        lineColor: isDark.value ? '#f59785' : '#d63d25',
        secondaryColor: isDark.value ? '#1f2933' : '#f6f6f7',
        tertiaryColor: isDark.value ? '#18181b' : '#ffffff',
        fontFamily:
          'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      },
    })

    const id = `quater-mermaid-${Math.random().toString(36).slice(2)}`
    const rendered = await mermaid.render(id, diagram)
    svg.value = rendered.svg
    error.value = null
  } catch (caught) {
    svg.value = ''
    error.value =
      caught instanceof Error ? caught.message : 'Unable to render diagram.'
  }
}

onMounted(() => {
  void renderDiagram()
})

watch(isDark, () => {
  void renderDiagram()
})
</script>

<template>
  <div class="q-mermaid" role="img">
    <div v-if="error" class="q-mermaid-error">
      <strong>Diagram could not be rendered.</strong>
      <span>{{ error }}</span>
    </div>
    <div v-else class="q-mermaid-svg" v-html="svg" />
  </div>
</template>
