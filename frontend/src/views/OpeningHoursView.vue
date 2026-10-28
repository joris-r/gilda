<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  addClosure,
  addSlot,
  ApiError,
  deleteClosure,
  deleteSlot,
  getAssociation,
  listClosures,
  listSlots,
  type Association,
  type Closure,
  type Slot,
  type Weekday,
} from '../api'
import { formatDate, shortDayWithYear, WEEKDAYS } from '../dates'

const props = defineProps<{ id: string }>()
const { t, locale } = useI18n()

const association = ref<Association>()
const slots = ref<Slot[]>([])
const closures = ref<Closure[]>([])
const message = ref<string>()

const weekday = ref<Weekday>('monday')
const start = ref('')
const end = ref('')
const first = ref('')
const last = ref('')
const label = ref('')

const isManager = computed(() => association.value?.role === 'manager')
const sortedSlots = computed(() =>
  [...slots.value].sort(
    (a, b) =>
      WEEKDAYS.indexOf(a.weekday) - WEEKDAYS.indexOf(b.weekday) ||
      a.start.localeCompare(b.start) ||
      a.end.localeCompare(b.end),
  ),
)
const sortedClosures = computed(() =>
  [...closures.value].sort((a, b) => a.first.localeCompare(b.first)),
)

async function load() {
  ;[association.value, slots.value, closures.value] = await Promise.all([
    getAssociation(props.id),
    listSlots(props.id),
    listClosures(props.id),
  ])
}

watch(() => props.id, load, { immediate: true })

function dates(closure: Closure) {
  const format = (iso: string) => formatDate(iso, locale.value, shortDayWithYear)
  return closure.first === closure.last
    ? format(closure.first)
    : `${format(closure.first)} – ${format(closure.last)}`
}

function failure(e: unknown, conflict?: string) {
  if (e instanceof ApiError && e.status === 409 && conflict) return conflict
  if (e instanceof ApiError && e.status === 400) return t('opening.invalid')
  return t('error')
}

async function createSlot() {
  message.value = undefined
  try {
    slots.value.push(await addSlot(props.id, weekday.value, start.value, end.value))
    start.value = ''
    end.value = ''
  } catch (e) {
    message.value = failure(e, t('opening.slotExists'))
  }
}

async function removeSlot(slot: Slot) {
  message.value = undefined
  try {
    await deleteSlot(props.id, slot.id)
    slots.value = slots.value.filter((s) => s.id !== slot.id)
  } catch (e) {
    message.value = failure(e)
  }
}

async function createClosure() {
  message.value = undefined
  try {
    closures.value.push(await addClosure(props.id, first.value, last.value, label.value || null))
    first.value = ''
    last.value = ''
    label.value = ''
  } catch (e) {
    message.value = failure(e)
  }
}

async function removeClosure(closure: Closure) {
  message.value = undefined
  try {
    await deleteClosure(props.id, closure.id)
    closures.value = closures.value.filter((c) => c.id !== closure.id)
  } catch (e) {
    message.value = failure(e)
  }
}
</script>

<template>
  <template v-if="association">
    <p class="hint">
      <RouterLink :to="`/associations/${id}`">← {{ association.name }}</RouterLink>
    </p>
    <h1>{{ t('opening.title') }}</h1>

    <h2>{{ t('opening.slots') }}</h2>
    <p v-if="!slots.length" class="hint">{{ t('opening.noSlots') }}</p>
    <ul v-else class="list">
      <li v-for="slot in sortedSlots" :key="slot.id">
        <span>{{ t(`weekdays.${slot.weekday}`) }}</span>
        <div class="actions">
          <span>{{ slot.start }}–{{ slot.end }}</span>
          <button v-if="isManager" type="button" class="link" @click="removeSlot(slot)">
            {{ t('opening.delete') }}
          </button>
        </div>
      </li>
    </ul>
    <form v-if="isManager" class="panel inline" @submit.prevent="createSlot">
      <label>
        {{ t('opening.day') }}
        <select v-model="weekday">
          <option v-for="day in WEEKDAYS" :key="day" :value="day">
            {{ t(`weekdays.${day}`) }}
          </option>
        </select>
      </label>
      <label>
        {{ t('opening.from') }}
        <input v-model="start" type="time" required />
      </label>
      <label>
        {{ t('opening.to') }}
        <input v-model="end" type="time" required />
      </label>
      <button type="submit">{{ t('opening.addSlot') }}</button>
    </form>

    <h2>{{ t('opening.closures') }}</h2>
    <p v-if="!closures.length" class="hint">{{ t('opening.noClosures') }}</p>
    <ul v-else class="list">
      <li v-for="closure in sortedClosures" :key="closure.id">
        <div>
          {{ dates(closure) }}
          <div v-if="closure.label" class="sub">{{ closure.label }}</div>
        </div>
        <button v-if="isManager" type="button" class="link" @click="removeClosure(closure)">
          {{ t('opening.delete') }}
        </button>
      </li>
    </ul>
    <form v-if="isManager" class="panel inline" @submit.prevent="createClosure">
      <label>
        {{ t('opening.first') }}
        <input v-model="first" type="date" required />
      </label>
      <label>
        {{ t('opening.last') }}
        <input v-model="last" type="date" required />
      </label>
      <label>
        {{ t('opening.label') }}
        <input v-model="label" />
      </label>
      <button type="submit">{{ t('opening.addClosure') }}</button>
    </form>
    <p v-if="message" class="error">{{ message }}</p>
  </template>
</template>

<style scoped>
.panel.inline {
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  align-items: end;
  margin-top: 12px;
}
</style>
