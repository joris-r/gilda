<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import {
  listAssociations,
  setRegistrationStatus,
  type HomeAssociation,
  type Registration,
} from '../api'
import { formatDate, formatRange, shortDay, today } from '../dates'
import { useLocation } from '../location'
import { takeNotice } from '../notice'

// The list carries no timezone: every association is in Europe/Paris for now.
const TIMEZONE = 'Europe/Paris'

const { t, locale } = useI18n()
const router = useRouter()
useLocation().value = { screen: 'myAssociations.title' }

const associations = ref<HomeAssociation[]>()
const error = ref('')
const notice = takeNotice()

onMounted(async () => {
  associations.value = await listAssociations()
})

/** R14: the association has a current planning period with no registration of mine. */
function remindsPeriod(association: HomeAssociation): boolean {
  const period = association.planning_period
  return period !== null && period.registrations === 0 && period.last >= today(TIMEZONE)
}

async function setStatus(
  association: HomeAssociation,
  registration: Registration,
  status: 'confirmed' | 'cancelled',
) {
  error.value = ''
  try {
    await setRegistrationStatus(association.id, registration.id, status)
    associations.value = await listAssociations()
  } catch {
    error.value = t('error')
  }
}
</script>

<template>
  <template v-if="associations">
    <p v-if="notice" class="message ok">{{ notice }}</p>
    <ul v-if="associations.length" class="list cards">
      <li v-for="association in associations" :key="association.id">
        <RouterLink class="name" :to="`/association/${association.slug}`">{{
          association.name
        }}</RouterLink>
        <span :class="['role', association.role]">{{ t(`roles.${association.role}`) }}</span>
        <div class="summary">
          <ul v-if="association.obsolete.length || association.upcoming.length" class="upcoming">
            <li
              v-for="registration in association.obsolete"
              :key="registration.id"
              class="obsolete"
            >
              <span class="slot">
                <span class="day">{{ formatDate(registration.date, locale, shortDay) }},</span>
                {{ ' ' }}
                <span class="time">{{ registration.start }}–{{ registration.end }}</span>
                {{ ' ' }}
                <span class="who">{{ registration.display_name }}</span>
                <span class="note">{{ t('myAssociations.obsolete') }}</span>
              </span>
              <button type="button" @click="setStatus(association, registration, 'cancelled')">
                {{ t('myAssociations.acknowledge') }}
              </button>
            </li>
            <li
              v-for="registration in association.upcoming"
              :key="registration.id"
              :class="registration.status"
            >
              <span class="slot">
                <span class="day">{{ formatDate(registration.date, locale, shortDay) }},</span>
                {{ ' ' }}
                <span class="time">{{ registration.start }}–{{ registration.end }}</span>
                {{ ' ' }}
                <span class="who">
                  {{ registration.display_name
                  }}{{ registration.status === 'proposed' ? ' ?' : '' }}
                </span>
              </span>
              <button
                v-if="registration.status === 'proposed'"
                type="button"
                @click="setStatus(association, registration, 'confirmed')"
              >
                {{ t('myAssociations.confirm') }}
              </button>
            </li>
          </ul>
          <p v-if="remindsPeriod(association)" class="reminder">
            <span>
              {{
                t('myAssociations.noRegistrationInPeriod', {
                  dates: formatRange(
                    association.planning_period!.first,
                    association.planning_period!.last,
                    locale,
                  ),
                })
              }}
            </span>
            <RouterLink class="choose" :to="`/association/${association.slug}`">
              {{ t('myAssociations.chooseSlots') }}
            </RouterLink>
          </p>
          <p v-else-if="!association.upcoming.length" class="hint">
            {{ t('myAssociations.noUpcoming') }}
          </p>
        </div>
      </li>
    </ul>
    <p v-else class="hint">{{ t('myAssociations.none') }}</p>
    <p v-if="error" class="error">{{ error }}</p>
    <p class="new">
      <button type="button" class="add" @click="router.push('/association/new')">
        <span aria-hidden="true">+</span> {{ t('myAssociations.create') }}
      </button>
    </p>
  </template>
</template>

<style scoped>
.message {
  margin: 0 0 12px;
}

.new {
  margin: 24px 0 0;
}

.list.cards {
  display: grid;
  gap: 16px;
  border-top: none;
}

.cards > li {
  gap: 12px;
  padding: 16px 20px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
}

.name {
  min-width: 0;
  font-size: 17px;
  font-weight: 600;
  text-decoration: none;
  overflow-wrap: anywhere;
}

.name:hover {
  text-decoration: underline;
}

.summary {
  display: grid;
  flex-basis: 100%;
  gap: 12px;
}

.summary p {
  margin: 0;
}

.upcoming {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

/* A registration: its coloured edge tells its state. */
.upcoming li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 4px 12px;
  min-height: 32px;
  padding: 6px 12px;
  border-bottom: none;
  background: var(--ok-soft);
  border-left: 3px solid var(--ok);
  border-radius: 4px;
}

.upcoming li.proposed {
  background: var(--warn-soft);
  border-left-color: var(--warn);
}

.upcoming li.obsolete {
  background: var(--bad-soft);
  border-left-color: var(--bad);
}

.upcoming button {
  padding: 4px 12px;
  font-size: 14px;
}

.slot {
  font-variant-numeric: tabular-nums;
}

/* A fixed width, so that the times of an association line up. */
.day {
  display: inline-block;
  min-width: 7.5em;
  font-weight: 600;
}

.time {
  white-space: nowrap;
}

/* No room for the column on a phone: the time follows the date. */
@media (max-width: 480px) {
  .day {
    min-width: 0;
  }
}

/* The name, as on the Schedule. */
.who {
  display: inline-block;
  max-width: 100%;
  margin-left: 12px;
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

.note {
  color: var(--bad);
}

.reminder {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 16px;
  padding: 10px 12px;
  background: var(--period-soft);
  border-radius: 6px;
}

.choose {
  font-weight: 600;
  color: var(--period);
  white-space: nowrap;
}
</style>
