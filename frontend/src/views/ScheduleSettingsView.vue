<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  addClosure,
  addSlot,
  ApiError,
  clearPlanningPeriod,
  deleteClosure,
  deletePreference,
  deleteSlot,
  getAssociation,
  getPlanningPeriod,
  listClosures,
  listPreferences,
  listSlots,
  setPlanningPeriod,
  setPreference,
  type Association,
  type Closure,
  type PlanningPeriod,
  type Preference,
  type PreferenceValue,
  type Slot,
  type Weekday,
} from '../api'
import PreferenceSelect from '../components/PreferenceSelect.vue'
import { formatDate, shortDayWithYear, WEEKDAYS } from '../dates'
import { useLocation } from '../location'
import { useSession } from '../session'

const props = defineProps<{ id: string }>()
const { t, locale } = useI18n()
const location = useLocation()
const { user } = useSession()

const association = ref<Association>()
const slots = ref<Slot[]>([])
const closures = ref<Closure[]>([])
const period = ref<PlanningPeriod | null>(null)
const preferences = ref<Preference[]>([])
const message = ref<string>()

const weekday = ref<Weekday>('monday')
const start = ref('09:00')
const end = ref('09:00')
// To follows From until the manager edits it.
const endEdited = ref(false)
const first = ref('')
const last = ref('')
const label = ref('')
const periodFirst = ref('')
const periodLast = ref('')

const isManager = computed(() => association.value?.role === 'manager')
const sortedSlots = computed(() =>
  [...slots.value].sort(
    (a, b) =>
      WEEKDAYS.indexOf(a.weekday) - WEEKDAYS.indexOf(b.weekday) ||
      a.start.localeCompare(b.start) ||
      a.end.localeCompare(b.end),
  ),
)
const sortedMembers = computed(() =>
  [...(association.value?.members ?? [])].sort((a, b) =>
    a.display_name.localeCompare(b.display_name),
  ),
)
const sortedClosures = computed(() =>
  [...closures.value].sort((a, b) => a.first.localeCompare(b.first)),
)

async function load() {
  ;[association.value, slots.value, closures.value, period.value, preferences.value] =
    await Promise.all([
      getAssociation(props.id),
      listSlots(props.id),
      listClosures(props.id),
      getPlanningPeriod(props.id),
      listPreferences(props.id),
    ])
  const { id, name } = association.value!
  location.value = { association: { id, name }, screen: 'settings.title' }
  periodFirst.value = period.value?.first ?? ''
  periodLast.value = period.value?.last ?? ''
}

watch(() => props.id, load, { immediate: true })

function dates(range: { first: string; last: string }) {
  const format = (iso: string) => formatDate(iso, locale.value, shortDayWithYear)
  return range.first === range.last
    ? format(range.first)
    : `${format(range.first)} – ${format(range.last)}`
}

function failure(e: unknown, conflict?: string) {
  if (e instanceof ApiError && e.status === 409 && conflict) return conflict
  if (e instanceof ApiError && e.status === 400) return t('settings.invalid')
  return t('error')
}

watch(start, (value) => {
  if (!endEdited.value) end.value = value
})

async function createSlot() {
  message.value = undefined
  try {
    const slot = await addSlot(props.id, weekday.value, start.value, end.value)
    slots.value.push(slot)
    endEdited.value = false
    start.value = slot.end
    end.value = slot.end
  } catch (e) {
    message.value = failure(e, t('settings.slotExists'))
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

function preferenceOf(slot: Slot, userId: string) {
  return preferences.value.find((p) => p.slot_id === slot.id && p.user_id === userId)?.value ?? null
}

async function choosePreference(slot: Slot, userId: string, value: PreferenceValue | null) {
  message.value = undefined
  const others = preferences.value.filter((p) => !(p.slot_id === slot.id && p.user_id === userId))
  try {
    if (value === null) {
      await deletePreference(props.id, slot.id, userId)
      preferences.value = others
    } else {
      preferences.value = [...others, await setPreference(props.id, slot.id, userId, value)]
    }
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

async function savePeriod() {
  message.value = undefined
  try {
    period.value = await setPlanningPeriod(props.id, periodFirst.value, periodLast.value)
  } catch (e) {
    message.value = failure(e)
  }
}

async function clearPeriod() {
  message.value = undefined
  try {
    await clearPlanningPeriod(props.id)
    period.value = null
    periodFirst.value = ''
    periodLast.value = ''
  } catch (e) {
    message.value = failure(e)
  }
}
</script>

<template>
  <template v-if="association">
    <h2>{{ t('settings.planningPeriod') }}</h2>
    <p :class="{ hint: !period }">{{ period ? dates(period) : t('settings.noPlanningPeriod') }}</p>
    <form v-if="isManager" class="panel inline" @submit.prevent="savePeriod">
      <label>
        {{ t('settings.first') }}
        <input v-model="periodFirst" type="date" required />
      </label>
      <label>
        {{ t('settings.last') }}
        <input v-model="periodLast" type="date" required />
      </label>
      <button type="submit">{{ t('settings.save') }}</button>
      <button v-if="period" type="button" class="link" @click="clearPeriod">
        {{ t('settings.clear') }}
      </button>
    </form>

    <h2>{{ t('settings.closures') }}</h2>
    <p v-if="!closures.length" class="hint">{{ t('settings.noClosures') }}</p>
    <ul v-else class="list">
      <li v-for="closure in sortedClosures" :key="closure.id">
        <div>
          {{ dates(closure) }}
          <div v-if="closure.label" class="sub">{{ closure.label }}</div>
        </div>
        <button v-if="isManager" type="button" class="link" @click="removeClosure(closure)">
          {{ t('settings.delete') }}
        </button>
      </li>
    </ul>
    <form v-if="isManager" class="panel inline" @submit.prevent="createClosure">
      <label>
        {{ t('settings.first') }}
        <input v-model="first" type="date" required />
      </label>
      <label>
        {{ t('settings.last') }}
        <input v-model="last" type="date" required />
      </label>
      <label>
        {{ t('settings.label') }}
        <input v-model="label" />
      </label>
      <button type="submit">{{ t('settings.addClosure') }}</button>
    </form>

    <h2>{{ t('settings.slots') }}</h2>
    <p v-if="!slots.length" class="hint">{{ t('settings.noSlots') }}</p>
    <ul v-else class="list">
      <li v-for="slot in sortedSlots" :key="slot.id">
        <span>{{ t(`weekdays.${slot.weekday}`) }}</span>
        <div class="actions">
          <span>{{ slot.start }}–{{ slot.end }}</span>
          <label>
            {{ t('settings.myPreference') }}
            <PreferenceSelect
              :value="preferenceOf(slot, user!.id)"
              @change="choosePreference(slot, user!.id, $event)"
            />
          </label>
          <button v-if="isManager" type="button" class="link" @click="removeSlot(slot)">
            {{ t('settings.delete') }}
          </button>
        </div>
      </li>
    </ul>
    <form v-if="isManager" class="panel inline" @submit.prevent="createSlot">
      <label>
        {{ t('settings.day') }}
        <select v-model="weekday">
          <option v-for="day in WEEKDAYS" :key="day" :value="day">
            {{ t(`weekdays.${day}`) }}
          </option>
        </select>
      </label>
      <label>
        {{ t('settings.from') }}
        <input v-model="start" type="time" required />
      </label>
      <label>
        {{ t('settings.to') }}
        <input v-model="end" type="time" required @input="endEdited = true" />
      </label>
      <button type="submit">{{ t('settings.addSlot') }}</button>
    </form>

    <template v-if="isManager && slots.length">
      <h2>{{ t('settings.membersPreferences') }}</h2>
      <div class="grid">
        <table>
          <thead>
            <tr>
              <th></th>
              <th v-for="slot in sortedSlots" :key="slot.id" scope="col">
                {{ t(`weekdaysShort.${slot.weekday}`) }} {{ slot.start }}–{{ slot.end }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="member in sortedMembers" :key="member.user_id">
              <th scope="row">{{ member.display_name }}</th>
              <td v-for="slot in sortedSlots" :key="slot.id">
                <PreferenceSelect
                  :value="preferenceOf(slot, member.user_id)"
                  :aria-label="`${member.display_name}, ${t(`weekdaysShort.${slot.weekday}`)} ${slot.start}–${slot.end}`"
                  @change="choosePreference(slot, member.user_id, $event)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <p v-if="message" class="error">{{ message }}</p>
  </template>
</template>

<style scoped>
.panel.inline {
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  align-items: end;
  margin-top: 12px;
}

.grid {
  overflow-x: auto;
}

.grid table {
  border-collapse: collapse;
}

.grid th,
.grid td {
  padding: 4px 8px;
  text-align: left;
  white-space: nowrap;
}

.grid th:first-child {
  position: sticky;
  left: 0;
  background: var(--bg);
}
</style>
