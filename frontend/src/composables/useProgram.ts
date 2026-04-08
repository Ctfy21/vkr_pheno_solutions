import { ref, watch } from 'vue'

export interface ProgramRef {
  id: string
  name: string
  abbreviation: string
}

const STORAGE_KEY = 'phenoplant_current_program'

function loadSaved(): ProgramRef | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const currentProgram = ref<ProgramRef | null>(loadSaved())

watch(currentProgram, (val) => {
  if (val) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(val))
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}, { deep: true })

export function useProgram() {
  function setProgram(p: ProgramRef) {
    currentProgram.value = p
  }

  function clearProgram() {
    currentProgram.value = null
    localStorage.removeItem(STORAGE_KEY)
  }

  return { currentProgram, setProgram, clearProgram }
}
