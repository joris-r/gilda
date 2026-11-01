<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import {
  createAssociation,
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
const creating = ref(false)
const name = ref('')
const error = ref('')

onMounted(async () => {
  associations.value = await listAssociations()
})

/** R14: the association has a current planning period with no registration of mine. */
function remindsPeriod(association: HomeAssociation): boolean {
  const period = association.planning_period
  return period !== null && period.registrations === 0 && period.last >= today(TIMEZONE)
}

async function confirm(association: HomeAssociation, registration: Registration) {
  error.value = ''
  try {
    await setRegistrationStatus(association.id, registration.id, 'confirmed')
    associations.value = await listAssociations()
  } catch {
    error.value = t('error')
  }
}

async function create() {
  error.value = ''
  try {
    const association = await createAssociation(name.value)
    await router.push(`/associations/${association.id}`)
  } catch {
    error.value = t('error')
  }
}
</script>

<template>
  <div class="toolbar">
    <button
      type="button"
      class="icon"
      :aria-label="t('myAssociations.create')"
      :title="t('myAssociations.create')"
      :aria-expanded="creating"
      @click="creating = !creating"
    >
      +
    </button>
  </div>
  <template v-if="associations">
    <ul v-if="associations.length" class="list">
      <li v-for="association in associations" :key="association.id">
        <RouterLink :to="`/associations/${association.id}`">{{ association.name }}</RouterLink>
        <span :class="['role', association.role]">{{ t(`roles.${association.role}`) }}</span>
        <div class="summary">
          <ul v-if="association.upcoming.length" class="upcoming">
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
                @click="confirm(association, registration)"
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
    <p v-if="error && !creating" class="error">{{ error }}</p>
  </template>
  <template v-if="creating">
    <h2>{{ t('myAssociations.create') }}</h2>
    <form class="panel" @submit.prevent="create">
      <label>
        {{ t('fields.name') }}
        <input v-model="name" required />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit">{{ t('myAssociations.submit') }}</button>
    </form>
  </template>
</template>
