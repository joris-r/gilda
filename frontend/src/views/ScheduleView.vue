<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  ApiError,
  getAssociation,
  getPlanningPeriod,
  getRegistrationCounts,
  getSchedule,
  listMemberAbsences,
  listNotes,
  listPreferences,
  listSlots,
  register,
  setRegistrationStatus,
  type Association,
  type Member,
  type MemberAbsence,
  type MemberNote,
  type PlanningPeriod,
  type Preference,
  type RegistrationCount,
  type Schedule,
  type Slot,
} from '../api'
import OccurrenceMenu from '../components/OccurrenceMenu.vue'
import ScheduleWeeks from '../components/ScheduleWeeks.vue'
import { addDays, mondayOf, today } from '../dates'
import { useLocation } from '../location'
import { actions, type Item } from '../schedule'
import { useSession } from '../session'

const FIRST_WEEKS = 6
const MORE_WEEKS = 4

const props = defineProps<{ id: string }>()
const { t } = useI18n()
const { user } = useSession()
const location = useLocation()

/** Today in the association's timezone, set once the association is loaded. */
const day0 = ref('')
const weeks = ref(FIRST_WEEKS)
const association = ref<Association>()
const schedule = ref<Schedule>({ occurrences: [], obsolete: [], closures: [] })
const period = ref<PlanningPeriod | null>(null)
const slots = ref<Slot[]>([])
const preferences = ref<Preference[]>([])
const counts = ref<RegistrationCount[] | null>(null)
const absences = ref<MemberAbsence[]>([])
const notes = ref<MemberNote[]>([])
const openItem = ref<Item>()
const anchor = ref<DOMRect>()
const message = ref<string>()

const firstMonday = computed(() => addDays(mondayOf(day0.value), -7))
const lastDay = computed(() => addDays(firstMonday.value, 7 * weeks.value - 1))
const isManager = computed(() => association.value?.role === 'manager')
const members = computed(() =>
  [...(association.value?.members ?? [])].sort((a, b) =>
    a.display_name.localeCompare(b.display_name),
  ),
)

/** Six weeks, or more to reach the week after the one that holds the period's last date. */
function firstWeeks(found: PlanningPeriod | null) {
  if (found === null) return FIRST_WEEKS
  const weekAfter = addDays(mondayOf(found.last), 7)
  let count = FIRST_WEEKS
  while (addDays(firstMonday.value, 7 * (count - 1)) < weekAfter) count++
  return count
}

/** The weeks failing to load still leave the header and an error message. */
async function load() {
  const [found, foundPeriod] = await Promise.allSettled([
    getAssociation(props.id),
    getPlanningPeriod(props.id),
  ])
  if (found.status === 'rejected') throw found.reason
  const { id, name, timezone } = found.value
  location.value = { association: { id, name } }
  day0.value = today(timezone)
  try {
    if (foundPeriod.status === 'rejected') throw foundPeriod.reason
    weeks.value = firstWeeks(foundPeriod.value)
    schedule.value = await getSchedule(props.id, firstMonday.value, lastDay.value)
    period.value = foundPeriod.value
  } catch {
    message.value = t('error')
  }
  association.value = found.value
  if (found.value.role === 'manager') await loadManagerData()
}

/** What the menu shows a manager of each member: preferences, counts, absences and notes. */
async function loadManagerData() {
  try {
    ;[slots.value, preferences.value, counts.value, absences.value, notes.value] =
      await Promise.all([
        listSlots(props.id),
        listPreferences(props.id),
        getRegistrationCounts(props.id),
        listMemberAbsences(props.id),
        listNotes(props.id),
      ])
  } catch {
    message.value = t('error')
  }
}

async function reload() {
  schedule.value = await getSchedule(props.id, firstMonday.value, lastDay.value)
  if (isManager.value) counts.value = await getRegistrationCounts(props.id)
}

async function more() {
  const from = addDays(lastDay.value, 1)
  const added = await getSchedule(props.id, from, addDays(from, 7 * MORE_WEEKS - 1))
  const known = new Set(schedule.value.closures.map((c) => c.id))
  schedule.value = {
    occurrences: [...schedule.value.occurrences, ...added.occurrences],
    obsolete: [...schedule.value.obsolete, ...added.obsolete],
    closures: [...schedule.value.closures, ...added.closures.filter((c) => !known.has(c.id))],
  }
  weeks.value += MORE_WEEKS
}

watch(() => props.id, load, { immediate: true })

const openActions = computed(() =>
  openItem.value ? actions(openItem.value, user.value?.id, isManager.value) : undefined,
)

function toggle(item: Item, rect: DOMRect) {
  if (openItem.value?.key === item.key) {
    close()
    return
  }
  openItem.value = item
  anchor.value = rect
}

function close() {
  openItem.value = undefined
}

onMounted(() => document.addEventListener('click', close))
onBeforeUnmount(() => document.removeEventListener('click', close))

async function act(run: () => Promise<unknown>) {
  message.value = undefined
  try {
    await run()
  } catch (e) {
    message.value = e instanceof ApiError && e.status === 409 ? t('schedule.taken') : t('error')
  }
  close()
  await reload()
}

function signUp(item: Item) {
  return act(() => register(props.id, user.value!.id, item.date, item.start, item.end))
}

function propose(item: Item, member: Member) {
  return act(() => register(props.id, member.user_id, item.date, item.start, item.end))
}

function setStatus(item: Item, status: 'confirmed' | 'cancelled') {
  return act(() => setRegistrationStatus(props.id, item.registration!.id, status))
}
</script>

<template>
  <template v-if="association">
    <p class="links">
      <RouterLink :to="`/associations/${id}/availability`">{{
        t('availability.title')
      }}</RouterLink>
      <RouterLink :to="`/associations/${id}/members`">{{ t('association.members') }}</RouterLink>
      <RouterLink :to="`/associations/${id}/settings`">{{ t('settings.title') }}</RouterLink>
    </p>
    <p v-if="message" class="error">{{ message }}</p>

    <ScheduleWeeks
      :schedule="schedule"
      :period="period"
      :day0="day0"
      :first-monday="firstMonday"
      :weeks="weeks"
      :open-key="openItem?.key"
      :user-id="user?.id"
      :is-manager="isManager"
      @toggle="toggle"
    />
    <button type="button" class="more" @click="more">{{ t('schedule.more') }}</button>

    <OccurrenceMenu
      v-if="openItem && openActions && anchor"
      :key="openItem.key"
      :item="openItem"
      :actions="openActions"
      :anchor="anchor"
      :members="members"
      :slots="slots"
      :preferences="preferences"
      :counts="counts"
      :absences="absences"
      :notes="notes"
      @sign-up="signUp(openItem)"
      @propose="propose(openItem, $event)"
      @set-status="setStatus(openItem, $event)"
      @close="close"
    />
  </template>
</template>

<style scoped>
.more {
  margin-top: 20px;
}
</style>
