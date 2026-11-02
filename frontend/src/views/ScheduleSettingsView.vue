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
  editClosure,
  editSlot,
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
import AppDialog from '../components/AppDialog.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import IconButton from '../components/IconButton.vue'
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

/**
 * The open dialog, with its error; a slot or closure dialog names what it edits, if any, and a
 * confirmation what it deletes.
 */
type Open =
  | { kind: 'period'; error: string }
  | { kind: 'slot'; error: string; editing?: Slot }
  | { kind: 'closure'; error: string; editing?: Closure }
  | { kind: 'deleteSlot'; slot: Slot }
  | { kind: 'deleteClosure'; closure: Closure }
  | { kind: 'clearPeriod' }
const open = ref<Open>()

const weekday = ref<Weekday>('monday')
const start = ref('09:00')
const end = ref('09:00')
// To follows From until the manager edits it.
const endEdited = ref(false)
/** The last slot added on this screen: R18 opens the next Add a slot from it. */
const lastAdded = ref<Slot>()
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

function dialogError(text: string) {
  if (open.value && 'error' in open.value) open.value.error = text
}

function openSlot() {
  weekday.value = lastAdded.value?.weekday ?? 'monday'
  start.value = lastAdded.value?.end ?? '09:00'
  end.value = start.value
  endEdited.value = false
  open.value = { kind: 'slot', error: '' }
}

function openSlotEdit(slot: Slot) {
  weekday.value = slot.weekday
  start.value = slot.start
  end.value = slot.end
  endEdited.value = true
  open.value = { kind: 'slot', error: '', editing: slot }
}

async function saveSlot(editing?: Slot) {
  try {
    if (editing) {
      const slot = await editSlot(props.id, editing.id, weekday.value, start.value, end.value)
      slots.value = slots.value.map((s) => (s.id === slot.id ? slot : s))
    } else {
      const slot = await addSlot(props.id, weekday.value, start.value, end.value)
      slots.value.push(slot)
      lastAdded.value = slot
    }
    open.value = undefined
  } catch (e) {
    dialogError(failure(e, t('settings.slotExists')))
  }
}

async function removeSlot(slot: Slot) {
  open.value = undefined
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

function openClosure() {
  first.value = ''
  last.value = ''
  label.value = ''
  open.value = { kind: 'closure', error: '' }
}

function openClosureEdit(closure: Closure) {
  first.value = closure.first
  last.value = closure.last
  label.value = closure.label ?? ''
  open.value = { kind: 'closure', error: '', editing: closure }
}

async function saveClosure(editing?: Closure) {
  try {
    if (editing) {
      const closure = await editClosure(
        props.id,
        editing.id,
        first.value,
        last.value,
        label.value || null,
      )
      closures.value = closures.value.map((c) => (c.id === closure.id ? closure : c))
    } else {
      closures.value.push(await addClosure(props.id, first.value, last.value, label.value || null))
    }
    open.value = undefined
  } catch (e) {
    dialogError(failure(e))
  }
}

async function removeClosure(closure: Closure) {
  open.value = undefined
  message.value = undefined
  try {
    await deleteClosure(props.id, closure.id)
    closures.value = closures.value.filter((c) => c.id !== closure.id)
  } catch (e) {
    message.value = failure(e)
  }
}

function openPeriod() {
  periodFirst.value = period.value?.first ?? ''
  periodLast.value = period.value?.last ?? ''
  open.value = { kind: 'period', error: '' }
}

async function savePeriod() {
  try {
    period.value = await setPlanningPeriod(props.id, periodFirst.value, periodLast.value)
    open.value = undefined
  } catch (e) {
    dialogError(failure(e))
  }
}

async function clearPeriod() {
  open.value = undefined
  message.value = undefined
  try {
    await clearPlanningPeriod(props.id)
    period.value = null
  } catch (e) {
    message.value = failure(e)
  }
}

function slotName(slot: Slot) {
  return `${t(`weekdays.${slot.weekday}`)} ${slot.start}–${slot.end}`
}

function closureQuestion(closure: Closure) {
  return closure.label
    ? t('settings.confirmDeleteClosure', { label: closure.label })
    : t('settings.confirmDeleteUnlabelledClosure', { date: dates(closure) })
}
</script>

<template>
  <template v-if="association">
    <h2>{{ t('settings.planningPeriod') }}</h2>
    <ul class="list">
      <li>
        <span :class="{ hint: !period }">{{
          period ? dates(period) : t('settings.noPlanningPeriod')
        }}</span>
        <div v-if="isManager" class="line-actions">
          <IconButton icon="edit" :label="t('settings.editPeriod')" @click="openPeriod" />
          <IconButton
            v-if="period"
            icon="delete"
            :label="t('settings.clearPeriod')"
            @click="open = { kind: 'clearPeriod' }"
          />
        </div>
      </li>
    </ul>

    <div class="section-head">
      <h2>{{ t('settings.closures') }}</h2>
      <button v-if="isManager" type="button" class="add" @click="openClosure">
        <span aria-hidden="true">+</span> {{ t('settings.addClosureTitle') }}
      </button>
    </div>
    <p v-if="!closures.length" class="hint">{{ t('settings.noClosures') }}</p>
    <ul v-else class="list">
      <li v-for="closure in sortedClosures" :key="closure.id">
        <div>
          {{ dates(closure) }}
          <div v-if="closure.label" class="sub">{{ closure.label }}</div>
        </div>
        <div v-if="isManager" class="line-actions">
          <IconButton
            icon="edit"
            :label="t('settings.editClosure')"
            @click="openClosureEdit(closure)"
          />
          <IconButton
            icon="delete"
            :label="t('settings.deleteClosure')"
            @click="open = { kind: 'deleteClosure', closure }"
          />
        </div>
      </li>
    </ul>

    <div class="section-head">
      <h2>{{ t('settings.slots') }}</h2>
      <button v-if="isManager" type="button" class="add" @click="openSlot">
        <span aria-hidden="true">+</span> {{ t('settings.addSlotTitle') }}
      </button>
    </div>
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
          <template v-if="isManager">
            <IconButton icon="edit" :label="t('settings.editSlot')" @click="openSlotEdit(slot)" />
            <IconButton
              icon="delete"
              :label="t('settings.deleteSlot')"
              @click="open = { kind: 'deleteSlot', slot }"
            />
          </template>
        </div>
      </li>
    </ul>

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

    <AppDialog
      v-if="open?.kind === 'period'"
      :title="t('settings.planningPeriod')"
      @close="open = undefined"
    >
      <form @submit.prevent="savePeriod">
        <div class="fields">
          <label>
            {{ t('settings.first') }}
            <input v-model="periodFirst" type="date" required />
          </label>
          <label>
            {{ t('settings.last') }}
            <input v-model="periodLast" type="date" required />
          </label>
        </div>
        <p v-if="open.error" class="error">{{ open.error }}</p>
        <div class="dialog-actions">
          <button type="submit">{{ t('settings.save') }}</button>
          <button type="button" class="link" @click="open = undefined">
            {{ t('dialog.cancel') }}
          </button>
        </div>
      </form>
    </AppDialog>

    <AppDialog
      v-if="open?.kind === 'closure'"
      :title="t(open.editing ? 'settings.editClosure' : 'settings.addClosureTitle')"
      @close="open = undefined"
    >
      <form @submit.prevent="saveClosure(open.editing)">
        <div class="fields">
          <label>
            {{ t('settings.first') }}
            <input v-model="first" type="date" required />
          </label>
          <label>
            {{ t('settings.last') }}
            <input v-model="last" type="date" required />
          </label>
        </div>
        <label>
          {{ t('settings.label') }}
          <input v-model="label" />
        </label>
        <p v-if="open.error" class="error">{{ open.error }}</p>
        <div class="dialog-actions">
          <button type="submit">
            {{ t(open.editing ? 'settings.save' : 'settings.addClosure') }}
          </button>
          <button type="button" class="link" @click="open = undefined">
            {{ t('dialog.cancel') }}
          </button>
        </div>
      </form>
    </AppDialog>

    <AppDialog
      v-if="open?.kind === 'slot'"
      :title="t(open.editing ? 'settings.editSlot' : 'settings.addSlotTitle')"
      @close="open = undefined"
    >
      <form @submit.prevent="saveSlot(open.editing)">
        <label>
          {{ t('settings.day') }}
          <select v-model="weekday">
            <option v-for="day in WEEKDAYS" :key="day" :value="day">
              {{ t(`weekdays.${day}`) }}
            </option>
          </select>
        </label>
        <div class="fields">
          <label>
            {{ t('settings.from') }}
            <input v-model="start" type="time" required />
          </label>
          <label>
            {{ t('settings.to') }}
            <input v-model="end" type="time" required @input="endEdited = true" />
          </label>
        </div>
        <p v-if="open.error" class="error">{{ open.error }}</p>
        <div class="dialog-actions">
          <button type="submit">
            {{ t(open.editing ? 'settings.save' : 'settings.addSlot') }}
          </button>
          <button type="button" class="link" @click="open = undefined">
            {{ t('dialog.cancel') }}
          </button>
        </div>
      </form>
    </AppDialog>

    <ConfirmDialog
      v-if="open?.kind === 'clearPeriod'"
      :question="t('settings.confirmClearPeriod')"
      :action="t('settings.clearAction')"
      @confirm="clearPeriod"
      @cancel="open = undefined"
    />
    <ConfirmDialog
      v-if="open?.kind === 'deleteClosure'"
      :question="closureQuestion(open.closure)"
      :action="t('settings.deleteAction')"
      @confirm="removeClosure(open.closure)"
      @cancel="open = undefined"
    />
    <ConfirmDialog
      v-if="open?.kind === 'deleteSlot'"
      :question="t('settings.confirmDeleteSlot', { slot: slotName(open.slot) })"
      :action="t('settings.deleteAction')"
      @confirm="removeSlot(open.slot)"
      @cancel="open = undefined"
    />
  </template>
</template>

<style scoped>
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
