# Design

- The interface follows the browser's light or dark preference.
- The accent colour is orange.
- Header: a long location is shortened on a narrow screen.
- Forms: on a narrow screen, a dialog spans the screen's width at its
  bottom.
- Registrations, on Schedule and My associations: green when
  confirmed, orange when proposed. On Schedule, red for a free
  occurrence and when cancelled; on My associations, red when
  obsolete, and a registration's name looks as on Schedule.
- Preference values, on My availability and Members' preferences:
  Preferred green, Possible orange, Unavailable red; "—" has none. A
  selector shows its value's colour.
- Members' preferences: when it scrolls horizontally, the member names
  stay in view.
- Schedule:
  - each week has one column per weekday on which an occurrence of the
    shown weeks falls; time runs down, on the same scale in every
    week, from the earliest start to the latest end of the shown
    occurrences, rounded to whole hours;
  - an occurrence, or an obsolete registration, is placed and sized by
    its start and end; those of a day that overlap sit side by side;
  - on a narrow screen, each week has one row per such weekday, and
    time runs from left to right;
  - the days before today look different from the others;
  - the planning period's lines and the background of the days within
    it share an accent colour, used by nothing else on the screen;
  - occurrences and obsolete registrations after the period's last
    date are greyed.
- Occurrence menu: each member's name has the background colour of
  their preference for the occurrence's slot, none when they have
  stated none, or grey when they are absent.
