# Members

As a manager:

```
(logo)  Jardin partagé des Lilas › Members                 Alice ▾

                                                  [+ Add a member]
  Alice                                        MANAGER   ✎
  alice@example.org
  Bruno                                      VOLUNTEER   ✎
  bruno@example.org
  Chloé  not joined yet                      VOLUNTEER   ✎
  chloe@example.org
  David  not joined yet                      VOLUNTEER   ✎
  david@example.org
  Emma                                       VOLUNTEER   ✎
  emma@example.org
  Show all 7 members

  Rename the association
  Change the association identifier
  Delete the association
```

Edit dialog:

```
┌ Chloé ───────────────────────────────────────── ✕ ┐
│ chloe@example.org                                 │
│ Role [Volunteer ▾]                                │
│ [Save]  Cancel                                    │
│                                                   │
│ SIGN-IN LINK                                      │
│ [Send link]  Revoke link                          │
│                                                   │
│ Remove from the association                       │
└───────────────────────────────────────────────────┘
```

Rename dialog:

```
┌ Rename the association ───────────────────────── ✕ ┐
│ Name [Jardin partagé des Lilas ]                   │
│ [Save]  Cancel                                     │
└────────────────────────────────────────────────────┘
```

Identifier dialog:

```
┌ Change the association identifier ──────────────────────────── ✕ ┐
│ Association identifier /association/[jardin-partage-des-lilas ]   │
│ [Save]  Cancel                                                    │
└───────────────────────────────────────────────────────────────────┘
```

Delete confirmation:

```
┌───────────────────────────────────────────────────┐
│ Delete Jardin partagé des Lilas? Its schedule and │
│ its members' registrations are erased. This       │
│ cannot be undone.                                 │
│ Type the association's name to confirm [        ] │
│ [Delete]  Cancel                                  │
└───────────────────────────────────────────────────┘
```

"Show all 7 members" clicked: the two other members show in its
place, in the list's order.

As a volunteer:

```
(logo)  Jardin partagé des Lilas › Members                 Chloé ▾

  Alice                                        MANAGER
  alice@example.org
  Bruno                                      VOLUNTEER
  bruno@example.org
  Chloé                                      VOLUNTEER
  chloe@example.org
```

Add dialog:

```
┌ Add a member ────────────────────────────────── ✕ ┐
│ Display name [                ]                   │
│ Email        [                ]                   │
│ Role         [Volunteer ▾]                        │
│ [Add member]  Cancel                              │
│ Chloé is already a member.                        │
└───────────────────────────────────────────────────┘
```

Confirmations, from the edit dialog:

```
┌───────────────────────────────────────────────────┐
│ Send Chloé's sign-in link by email?               │
│ [Send]  Cancel                                    │
└───────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────┐
│ Revoke Chloé's sign-in link?                      │
│ [Revoke]  Cancel                                  │
└───────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────┐
│ Remove Chloé from the association? Their upcoming │
│ registrations are cancelled.                      │
│ [Remove]  Cancel                                  │
└───────────────────────────────────────────────────┘
```

Messages, above the list: "Chloé added.", "Chloé is now manager.",
"Chloé's sign-in link is sent.", "Chloé's sign-in link is revoked.",
"Chloé is removed.", "The association is now Jardin partagé des
Lilas.", "The association identifier is now jardin-partage."
