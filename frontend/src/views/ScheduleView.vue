<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  ApiError,
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
import UnknownAssociation from '../components/UnknownAssociation.vue'
import { addDays, today } from '../dates'
import { useAssociationBySlug } from '../associationBySlug'
import { useLocation } from '../location'
import { actions, appendSchedule, MORE_WEEKS, weeksBetween, type Item } from '../schedule'
import { useSession } from '../session'

const props = defineProps<{ slug: string }>()
const { id, unknown, read } = useAssociationBySlug(() => props.slug)
const { t } = useI18n()
const { user } = useSession()
const location = useLocation()

/** Today in the association's timezone, set once the association is loaded. */
const day0 = ref('')
const firstMonday = ref('')
const weeks = ref(0)
const association = ref<Association>()
const schedule = ref<Schedule>({ from: '', to: '', occurrences: [], obsolete: [], closures: [] })
const period = ref<PlanningPeriod | null>(null)
const slots = ref<Slot[]>([])
const preferences = ref<Preference[]>([])
const counts = ref<RegistrationCount[] | null>(null)
const absences = ref<MemberAbsence[]>([])
const notes = ref<MemberNote[]>([])
const openItem = ref<Item>()
const anchor = ref<DOMRect>()
const message = ref<string>()

const lastDay = computed(() => addDays(firstMonday.value, 7 * weeks.value - 1))
const isManager = computed(() => association.value?.role === 'manager')
const members = computed(() =>
  [...(association.value?.members ?? [])].sort((a, b) =>
    a.display_name.localeCompare(b.display_name),
  ),
)

/** The weeks failing to load still leave the header and an error message. */
async function load() {
  association.value = undefined
  const found = await read()
  if (!found) return
  location.value = { association: { slug: found.slug, name: found.name } }
  day0.value = today(found.timezone)
  const [foundPeriod, foundSchedule] = await Promise.allSettled([
    getPlanningPeriod(id.value),
    getSchedule(id.value),
  ])
  try {
    if (foundPeriod.status === 'rejected') throw foundPeriod.reason
    if (foundSchedule.status === 'rejected') throw foundSchedule.reason
    const { from, to } = foundSchedule.value
    firstMonday.value = from
    weeks.value = weeksBetween(from, to)
    schedule.value = foundSchedule.value
    period.value = foundPeriod.value
  } catch {
    message.value = t('error')
  }
  association.value = found
  if (found.role === 'manager') await loadManagerData()
}

/** What the menu shows a manager of each member: preferences, counts, absences and notes. */
async function loadManagerData() {
  try {
    ;[slots.value, preferences.value, counts.value, absences.value, notes.value] =
      await Promise.all([
        listSlots(id.value),
        listPreferences(id.value),
        getRegistrationCounts(id.value),
        listMemberAbsences(id.value),
        listNotes(id.value),
      ])
  } catch {
    message.value = t('error')
  }
}

async function reload() {
  schedule.value = await getSchedule(id.value, { from: firstMonday.value, to: lastDay.value })
  if (isManager.value) counts.value = await getRegistrationCounts(id.value)
}

async function more() {
  const from = addDays(lastDay.value, 1)
  const added = await getSchedule(id.value, { from, to: addDays(from, 7 * MORE_WEEKS - 1) })
  schedule.value = appendSchedule(schedule.value, added)
  weeks.value += MORE_WEEKS
}

watch(() => props.slug, load, { immediate: true })

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
  return act(() => register(id.value, user.value!.id, item.date, item.start, item.end))
}

function propose(item: Item, member: Member) {
  return act(() => register(id.value, member.user_id, item.date, item.start, item.end))
}

function setStatus(item: Item, status: 'confirmed' | 'cancelled') {
  return act(() => setRegistrationStatus(id.value, item.registration!.id, status))
}
</script>

<template>
  <UnknownAssociation v-if="unknown" />
  <template v-else-if="association">
    <p class="links">
      <RouterLink :to="`/associations/${slug}/availability`">{{
        t('availability.title')
      }}</RouterLink>
      <RouterLink :to="`/associations/${slug}/members`">{{ t('association.members') }}</RouterLink>
      <RouterLink :to="`/associations/${slug}/settings`">{{ t('settings.title') }}</RouterLink>
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
