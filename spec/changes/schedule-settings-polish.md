# Schedule settings polish

The Add slot form starts from useful times, and Members' preferences
keeps the member names in view.

## `/associations/{id}/settings`: Schedule settings

New rules on the Add slot form:

- R17: The form opens with From at 09:00 and To at 09:00. Changing
  From sets To to the same time, until the manager changes To.
- R18: After a slot is added, Day keeps its value, and From and To
  both show the added slot's end; To follows From again as in R17.

New rule on Members' preferences:

- When the table is wider than the screen and scrolls horizontally,
  the member names stay in view (not testable).
