<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  addMember,
  ApiError,
  changeRole,
  deleteAssociation,
  getAssociation,
  removeMember,
  renameAssociation,
  revokeMemberLink,
  sendMemberLink,
  type Association,
  type Member,
  type Role,
} from '../api'
import AppDialog from '../components/AppDialog.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import IconButton from '../components/IconButton.vue'
import { useLocation } from '../location'
import { leaveNotice } from '../notice'
import { useSession } from '../session'

/** Members shown before "Show all". */
const FIRST_MEMBERS = 5

const props = defineProps<{ id: string }>()
const { t } = useI18n()
const router = useRouter()
const { user } = useSession()
const location = useLocation()

const association = ref<Association>()
const message = ref<{ text: string; ok: boolean }>()
const showAll = ref(false)

/** The open Add a member dialog, with its error. */
const adding = ref<{ error: string }>()
const displayName = ref('')
const email = ref('')
const role = ref<Role>('volunteer')

/** The member whose edit dialog is open, with the role chosen in it and its error. */
const editing = ref<{ member: Member; role: Role; error: string }>()
/** The action of the edit dialog waiting for confirmation. */
const confirming = ref<'revoke' | 'send' | 'remove'>()

/** The open Rename the association dialog, with the name typed in it and its error. */
const renaming = ref<{ name: string; error: string }>()

/** The open confirmation of deleting the association, with the name typed in it and its error. */
const deleting = ref<{ typed: string; error: string }>()

const questions = {
  revoke: 'association.confirmRevokeLink',
  send: 'association.confirmSendLink',
  remove: 'association.confirmRemove',
}
const actions = {
  revoke: 'association.revoke',
  send: 'association.send',
  remove: 'association.remove',
}

const isManager = computed(() => association.value?.role === 'manager')
const members = computed(() =>
  [...(association.value?.members ?? [])].sort(
    (a, b) =>
      Number(b.role === 'manager') - Number(a.role === 'manager') ||
      a.display_name.localeCompare(b.display_name),
  ),
)
const shownMembers = computed(() =>
  showAll.value ? members.value : members.value.slice(0, FIRST_MEMBERS),
)

async function load() {
  const found = await getAssociation(props.id)
  association.value = found
  location.value = {
    association: { id: found.id, name: found.name },
    screen: 'association.members',
  }
}

watch(() => props.id, load, { immediate: true })

function openAdd() {
  displayName.value = ''
  email.value = ''
  role.value = 'volunteer'
  adding.value = { error: '' }
}

function openEdit(member: Member) {
  message.value = undefined
  editing.value = { member, role: member.role, error: '' }
}

function closeEdit() {
  editing.value = undefined
  confirming.value = undefined
}

async function saveRole() {
  const edit = editing.value!
  if (edit.role === edit.member.role) return closeEdit()
  try {
    const updated = await changeRole(props.id, edit.member.user_id, edit.role)
    edit.member.role = updated.role
    if (association.value && updated.user_id === user.value?.id)
      association.value.role = updated.role
    closeEdit()
    message.value = {
      ok: true,
      text: t('association.roleChanged', {
        name: updated.display_name,
        role: t(`roleNames.${updated.role}`),
      }),
    }
  } catch (e) {
    edit.error =
      e instanceof ApiError && e.status === 409 ? t('association.lastManager') : t('error')
  }
}

async function remove(member: Member) {
  try {
    await removeMember(props.id, member.user_id)
  } catch (e) {
    editing.value!.error =
      e instanceof ApiError && e.status === 409 ? t('association.lastManager') : t('error')
    return
  }
  closeEdit()
  if (member.user_id === user.value?.id) return router.push('/')
  await load()
  message.value = { ok: true, text: t('association.removed', { name: member.display_name }) }
}

async function confirmAction() {
  const { member } = editing.value!
  const action = confirming.value
  confirming.value = undefined
  if (action === 'remove') return remove(member)
  try {
    if (action === 'revoke') {
      await revokeMemberLink(props.id, member.user_id)
      member.access_link = false
    } else {
      member.access_link = (await sendMemberLink(props.id, member.user_id)).access_link
    }
    closeEdit()
    const done = action === 'revoke' ? 'association.linkRevoked' : 'association.linkSent'
    message.value = { ok: true, text: t(done, { name: member.display_name }) }
  } catch (e) {
    editing.value!.error =
      action === 'send' && e instanceof ApiError && e.status === 503
        ? t('association.linkNotSent', { name: member.display_name })
        : t('error')
  }
}

async function add() {
  const name = displayName.value
  try {
    const member = await addMember(props.id, name, email.value, role.value)
    await load()
    adding.value = undefined
    message.value = { ok: true, text: t('association.added', { name: member.display_name }) }
  } catch (e) {
    adding.value!.error =
      e instanceof ApiError && e.status === 409
        ? t('association.alreadyMember', { name })
        : t('error')
  }
}

function openRename() {
  message.value = undefined
  renaming.value = { name: association.value!.name, error: '' }
}

async function saveName() {
  const rename = renaming.value!
  if (!rename.name) return
  if (rename.name === association.value!.name) {
    renaming.value = undefined
    return
  }
  try {
    const { name } = await renameAssociation(props.id, rename.name)
    association.value!.name = name
    location.value = { association: { id: props.id, name }, screen: 'association.members' }
    renaming.value = undefined
    message.value = { ok: true, text: t('association.renamed', { name }) }
  } catch {
    rename.error = t('error')
  }
}

async function confirmDelete() {
  const { name } = association.value!
  const confirmation = deleting.value!
  if (confirmation.typed !== name) return
  try {
    await deleteAssociation(props.id)
  } catch {
    confirmation.error = t('error')
    return
  }
  leaveNotice(t('association.deleted', { name }))
  await router.push('/')
}
</script>

<template>
  <template v-if="association">
    <div v-if="isManager" class="toolbar">
      <button type="button" class="add" @click="openAdd">
        <span aria-hidden="true">+</span> {{ t('association.addMember') }}
      </button>
    </div>
    <p v-if="message" :class="['message', message.ok ? 'ok' : 'error']">{{ message.text }}</p>
    <ul class="list">
      <li v-for="member in shownMembers" :key="member.user_id">
        <div>
          {{ member.display_name }}
          <span v-if="!member.email_verified" class="no-account">{{
            t('association.notJoined')
          }}</span>
          <div class="sub">{{ member.email }}</div>
        </div>
        <div class="actions">
          <span :class="['role', member.role]">{{ t(`roles.${member.role}`) }}</span>
          <IconButton
            v-if="isManager"
            icon="edit"
            :label="t('association.edit', { name: member.display_name })"
            @click="openEdit(member)"
          />
        </div>
      </li>
    </ul>
    <p v-if="!showAll && members.length > FIRST_MEMBERS" class="more">
      <button type="button" class="link" @click="showAll = true">
        {{ t('association.showAll', { n: members.length }) }}
      </button>
    </p>
    <div v-if="isManager" class="remove">
      <p class="rename">
        <button type="button" class="link" @click="openRename">
          {{ t('association.renameAssociation') }}
        </button>
      </p>
      <button type="button" class="link danger" @click="deleting = { typed: '', error: '' }">
        {{ t('association.deleteAssociation') }}
      </button>
    </div>

    <AppDialog
      v-if="renaming"
      :title="t('association.renameAssociation')"
      @close="renaming = undefined"
    >
      <form @submit.prevent="saveName">
        <label>
          {{ t('fields.name') }}
          <input v-model="renaming.name" autocomplete="off" />
        </label>
        <p v-if="renaming.error" class="error">{{ renaming.error }}</p>
        <div class="dialog-actions">
          <button type="submit" :disabled="!renaming.name">{{ t('association.save') }}</button>
          <button type="button" class="link" @click="renaming = undefined">
            {{ t('dialog.cancel') }}
          </button>
        </div>
      </form>
    </AppDialog>

    <AppDialog v-if="deleting" @close="deleting = undefined">
      <form @submit.prevent="confirmDelete">
        <p>{{ t('association.confirmDelete', { name: association.name }) }}</p>
        <label>
          {{ t('association.typeName') }}
          <input v-model="deleting.typed" autocomplete="off" />
        </label>
        <p v-if="deleting.error" class="error">{{ deleting.error }}</p>
        <div class="dialog-actions">
          <button type="submit" :disabled="deleting.typed !== association.name">
            {{ t('association.delete') }}
          </button>
          <button type="button" class="link" @click="deleting = undefined">
            {{ t('dialog.cancel') }}
          </button>
        </div>
      </form>
    </AppDialog>

    <AppDialog v-if="adding" :title="t('association.addMember')" @close="adding = undefined">
      <form @submit.prevent="add">
        <label>
          {{ t('fields.displayName') }}
          <input v-model="displayName" required />
        </label>
        <label>
          {{ t('fields.email') }}
          <input v-model="email" type="email" required />
        </label>
        <label>
          {{ t('fields.role') }}
          <select v-model="role">
            <option value="volunteer">{{ t('roles.volunteer') }}</option>
            <option value="manager">{{ t('roles.manager') }}</option>
          </select>
        </label>
        <p v-if="adding.error" class="error">{{ adding.error }}</p>
        <div class="dialog-actions">
          <button type="submit">{{ t('association.submit') }}</button>
          <button type="button" class="link" @click="adding = undefined">
            {{ t('dialog.cancel') }}
          </button>
        </div>
      </form>
    </AppDialog>

    <AppDialog v-if="editing" :title="editing.member.display_name" @close="closeEdit">
      <form @submit.prevent="saveRole">
        <p class="sub">{{ editing.member.email }}</p>
        <label>
          {{ t('fields.role') }}
          <select v-model="editing.role">
            <option value="volunteer">{{ t('roles.volunteer') }}</option>
            <option value="manager">{{ t('roles.manager') }}</option>
          </select>
        </label>
        <p v-if="editing.error" class="error">{{ editing.error }}</p>
        <div class="dialog-actions">
          <button type="submit">{{ t('association.save') }}</button>
          <button type="button" class="link" @click="closeEdit">{{ t('dialog.cancel') }}</button>
        </div>
      </form>
      <h3>{{ t('association.signInLink') }}</h3>
      <div class="dialog-actions">
        <button type="button" @click="confirming = 'send'">
          {{ t('association.sendLink') }}
        </button>
        <button
          v-if="editing.member.access_link"
          type="button"
          class="link"
          @click="confirming = 'revoke'"
        >
          {{ t('association.revokeLink') }}
        </button>
      </div>
      <div class="dialog-actions remove">
        <button type="button" class="link danger" @click="confirming = 'remove'">
          {{ t('association.removeMember') }}
        </button>
      </div>
    </AppDialog>

    <ConfirmDialog
      v-if="editing && confirming"
      :question="t(questions[confirming], { name: editing.member.display_name })"
      :action="t(actions[confirming])"
      @confirm="confirmAction"
      @cancel="confirming = undefined"
    />
  </template>
</template>

<style scoped>
.more {
  margin: 12px 0 0;
}

.message {
  margin: 0 0 12px;
}

.remove {
  margin-top: 24px;
}

.rename {
  margin: 0 0 12px;
}

.danger {
  color: var(--danger);
}
</style>
