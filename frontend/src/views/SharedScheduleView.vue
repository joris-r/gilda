<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApiError, getShared, getSharedSchedule, type PlanningPeriod, type Schedule } from '../api'
import ScheduleWeeks from '../components/ScheduleWeeks.vue'
import { addDays, today } from '../dates'
import { useLocation } from '../location'
import { appendSchedule, MORE_WEEKS, weeksBetween } from '../schedule'

const props = defineProps<{ token: string }>()
const { t } = useI18n()
const location = useLocation()

/** Today in the association's timezone. */
const day0 = ref('')
const firstMonday = ref('')
const weeks = ref(0)
const schedule = ref<Schedule>()
const period = ref<PlanningPeriod | null>(null)
const message = ref<string>()

async function load() {
  schedule.value = undefined
  message.value = undefined
  try {
    const [shared, found] = await Promise.all([
      getShared(props.token),
      getSharedSchedule(props.token),
    ])
    location.value = { title: shared.name }
    day0.value = today(shared.timezone)
    period.value = shared.planning_period
    firstMonday.value = found.from
    weeks.value = weeksBetween(found.from, found.to)
    schedule.value = found
  } catch (e) {
    message.value =
      e instanceof ApiError && e.status === 404 ? t('verifyEmail.invalid') : t('error')
  }
}

async function more() {
  if (!schedule.value) return
  const from = addDays(schedule.value.to, 1)
  try {
    const added = await getSharedSchedule(props.token, {
      from,
      to: addDays(from, 7 * MORE_WEEKS - 1),
    })
    schedule.value = appendSchedule(schedule.value, added)
    weeks.value += MORE_WEEKS
  } catch {
    message.value = t('error')
  }
}

watch(() => props.token, load, { immediate: true })
</script>

<template>
  <p v-if="message" :class="{ error: schedule }">{{ message }}</p>
  <template v-if="schedule">
    <ScheduleWeeks
      :schedule="schedule"
      :period="period"
      :day0="day0"
      :first-monday="firstMonday"
      :weeks="weeks"
      :open-key="undefined"
      :user-id="undefined"
      :is-manager="false"
    />
    <button type="button" class="more" @click="more">{{ t('schedule.more') }}</button>
  </template>
</template>

<style scoped>
.more {
  margin-top: 20px;
}
</style>
