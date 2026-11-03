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

// The list carries no timezone: every association is in Europe/Paris for now.
const TIMEZONE = 'Europe/Paris'

const { t, locale } = useI18n()
const router = useRouter()
useLocation().value = { screen: 'myAssociations.title' }

const associations = ref<HomeAssociation[]>()
const error = ref('')

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
    <ul v-if="associations.length" class="list">
      <li v-for="association in associations" :key="association.id">
        <RouterLink :to="`/associations/${association.id}`">{{ association.name }}</RouterLink>
        <span :class="['role', association.role]">{{ t(`roles.${association.role}`) }}</span>
        <div class="summary">
          <ul v-if="association.obsolete.length || association.upcoming.length" class="upcoming">
            <li v-for="registration in association.obsolete" :key="registration.id">
              <span>
                {{ formatDate(registration.date, locale, shortDay) }}, {{ registration.start }}–{{
                  registration.end
                }}{{ t('myAssociations.obsolete') }}
              </span>
              <button type="button" @click="setStatus(association, registration, 'cancelled')">
                {{ t('myAssociations.acknowledge') }}
              </button>
            </li>
            <li v-for="registration in association.upcoming" :key="registration.id">
              <span>
                {{ formatDate(registration.date, locale, shortDay) }}, {{ registration.start }}–{{
                  registration.end
                }}
                <template v-if="registration.status === 'proposed'">?</template>
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
          <p v-if="remindsPeriod(association)" class="hint">
            {{
              t('myAssociations.noRegistrationInPeriod', {
                dates: formatRange(
                  association.planning_period!.first,
                  association.planning_period!.last,
                  locale,
                ),
              })
            }}
            <RouterLink :to="`/associations/${association.id}`">
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
      <button type="button" class="add" @click="router.push('/associations/new')">
        <span aria-hidden="true">+</span> {{ t('myAssociations.create') }}
      </button>
    </p>
  </template>
</template>

<style scoped>
.new {
  margin: 24px 0 0;
}
</style>
