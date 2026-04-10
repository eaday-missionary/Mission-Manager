===RULESET===
1. Each Person is part of an area, and a zone. An area is contained within a zone, and there are 6 zones in total.

2. Every person on this list travels in a companionship, usually consisting of two people, but sometimes three. Each person has a starting companionship and an ending companionship. People who are companions in the starting companionship will always begin in the same area together. People who are assigned together in an ending companionship will always travel to the same area and must eventually reunite in their assigned destination. People who are together in a starting companionship will ALWAYS travel together to the terminal to drop off the companion who is leaving the area, or when all members of the companionship are leaving the area. A `Current Companion` or `New Companion` field may contain one, two, or three names, but never more than three total people in that companionship.

3. All times, terminals, companionships, zones, or areas MUST not be changed.

=== FORMAT RULES ===

- In the instructions below, /newline/ is a marker. Do not print /newline/ in the output. Instead, start a new line at that point.

- All companion names are exactly "FirstName LastName", case-insensitive, trimmed, single spaces. Multiple companions are separated by "&".

- When comparing `Current Companion` and `New Companion`, compare them as exact sets of names, not raw text. Ignore case, extra spaces, and the order of the names.

- If companion row cannot be found, do NOT treat it as blank; instead print an error.

- If one companion row is missing but other companion rows are valid, print the error for the missing row and continue using the valid rows only if the remaining logic is still deterministic.

- If no time can be found when a time value is needed, replace the time value with "00:00".

- `00:00` is a fallback display value. Do NOT let fallback-only `00:00` values decide "earliest" or "latest" ordering unless every candidate time for that comparison is also fallback-only.

- Treat each instance of "Trainee" as it's own unique person. It is just a placeholder name.

- When a comparison uses a companion's arrival time, always use that companion's final arrival time after all legs of travel.

- When comparing terminals or locations, ignore case, extra spaces, the word `Subway`, and minor punctuation/spacing differences.

- If a rule references `Current Companion` or `New Companion` and there are multiple names, apply the multi-companion rules below. Do NOT choose one companion arbitrarily.

- If a person appears in both the starting companionship and ending companionship, that overlapping companion is already reunited and should not by themselves create a new dropoff or wait target. Only the companions who are changing in or out should drive handoff routing. If this still leaves more than one possible reunion terminal, add the transfer editor flag `multiple new companions, manual confirmation required`.

1. print(First Name + " " + Last Name)

/newline/

2. IF Departure Terminal is NOT blank: 
- IF Departure Time AND Arrival Time are blank:
-- at the very top of the schedule block, just below their name, print("WARNING -- You must purchase the " + Departure Terminal + " ticket in person")
-- /newline/

3. IF 2nd Departure Terminal is NOT blank: 
- IF 2nd Departure Time AND 2nd Arrival Time are blank:
-- at the very top of the schedule block, just below their name, print("WARNING -- You must purchase the " + 2nd Departure Terminal + " ticket in person")
-- /newline/

4. IF New Zone = "수지 Training":
- IF New Zone = "수지 Training" AND Departure Terminal.contains("Subway"):
-- print("Arrive at the mission office before 10:45.")
-- Skip all other instructions except for step 16.

5. IF Departure Terminal.contains("Subway") OR 2nd Departure Terminal.contains("Subway"):
- remove the "Subway" text from the Departure Terminal value AND the 2nd Departure Terminal value.
- print("!!!!! Make sure your bus card is filled up BEFORE transfer day !!!!!")
/newline/

6. IF Departure Terminal is blank (-):
- If Current Companion = New Companion:
-- For multiple names, `Current Companion = New Companion` means exact set equality.
-- print("화이팅!!!").
-- Skip ALL other instructions for this person except step 14. This will override everything else.
- ELSE
-- From here, only do steps 7, 8, 9, and 16.

7. IF Pre Travel is NOT blank (-):
- print("please arrive at the " + Pre Travel + " apartment by Thursday night")

8. IF Staying or Leaving? = "Yes":
- This means they are staying. But they will still have to travel to the terminal with their current companion to drop them off, and then either pick up their new companion who could already be waiting, OR they will have to wait until their new companions arrive. Refer to the IF statements below to determine the logic.
- If there are multiple Current Companions who are leaving, print one dropoff instruction per departing Current Companion.
- Default dropoff order is: earliest valid Departure Time first. Any departing companion with no usable Departure Time must be dropped off after all companions with usable times. If multiple such companions remain, preserve the listed order.
- If one dropoff terminal is the same terminal where the relevant New Companion handoff will happen, visit that terminal last, even if its Departure Time is earlier.
- If there are multiple New Companions, use the earliest valid final arrival time to determine the reunion terminal/time, and add the transfer editor flag `multiple new companions, manual confirmation required`.
- If multiple New Companions tie for earliest valid final arrival time and the reunion terminals are different, add the transfer editor flag `multiple new companions, manual confirmation required`.
- If the chosen New Companion's final leg of travel is a subway leg and no final arrival time is available, print("Please communicate with your new companion to determine a meetup time in advance.") instead of any wait / will-be-waiting sentence.
- If the final dropoff terminal does NOT match the reunion terminal of the chosen New Companion, add the transfer editor flag `companion pickup error`.
- If `companion pickup error` was added, print("[New companion is arriving at " + reunion terminal of the chosen New Companion + "]") after the final dropoff instruction. If the chosen New Companion's final leg of travel is a subway leg and no final arrival time is available, also print("Please communicate with your new companion to determine a meetup time in advance.").
- IF they will have to wait for their New Companion (if the final arrival time of their New Companion is greater than the departure time of their Current Companion, check both Arrival Time and 2nd Arrival Time to determine the final arrival time of their New Companion):
-- print("Drop off " + Current Companion + " at " +  Departure Terminal of their Current Companion + ". Wait at " + Departure Terminal of their Current Companion + " until your new companion, " + New Companion + ", arrives there at " + TIME (find the time that their New Companion will arrive and insert it here)) + "."
- IF they will NOT have to wait for their New Companion (if the final arrival time of their New Companion is less than or equal to the Departure Time of their Current Companion, check both Arrival Time and 2nd Arrival Time to determine the final arrival time of their New Companion):
-- print("Drop off " + Current Companion + " at " +  Departure Terminal of their Current Companion + ". Your new companion, " + New Companion + ", will be waiting.")
- If the compared times are exactly equal, treat that as `will be waiting`.
- From here, only do step 14.

9. IF Staying or Leaving? = "No":
- print("Travel to " + Departure Terminal + " with " + Current Companion + ".")
- If the person has multiple Current Companions, and one or more of those Current Companions are also leaving before this person's Departure Time, print the needed dropoff instruction(s) for those earlier-departing companions first, and then print this person's own travel instruction.
- If both this person and another leaving Current Companion depart from the same normalized terminal, different Departure Times alone do NOT create a conflict.
- If both this person and another leaving Current Companion depart from different normalized terminals, the person with the latest Departure Time must receive the transfer editor flag `traveling alone, needs manual inspection`.
/newline/

10. IF Departure Terminal.contains("Subway"):
- remove the "Subway" text from the Departure Terminal value AND the Arrival Terminal value.
- print("Travel to " + Departure Terminal + " and ride the " + Departure Time + " to " + Arrival Terminal + ". Leave in time to arrive there at " + Arrival Time + ".")
- IF Second Leg? = "no":
-- print("There, you will meet your new companion, " + New Companion + ".")
- /newline/
ELSE:
- print("Departure Location: " + Departure Terminal)
- print("Departure Time: " + Departure Time)
/newline/
- print("Arrival Time: " + Arrival Time)
- print("Arrival Location: " + Arrival Terminal)
/newline/
- IF New Zone = "수지 Training" AND Departure Terminal.DoesNotContain("Subway"):
-- print("Travel to the mission office from there. Arrive before 10:45.")
-- /newline/

11. IF Second Leg? = "yes":
- Skip step 12.
- IF Second Leg = "yes" AND Arrival Terminal is NOT EQUAL to 2nd Departure Terminal:
-- print("WARNING You need to travel to " + 2nd Departure Terminal + " for your second leg of travel.")
-- /newline/

12. IF Staying or Leaving? = "No":
- print("Notes: " + NOTES)
- In the "Notes" portion, choose notes to include from the following list below. Choose instructions from the list based on whether the given conditions are met or not (possible instructions to be printed are marked at the beginning of the line with "*"):

NOTES:
-- IF Staying or Leaving? = "No":
--- IF there are multiple New Companions, use the earliest valid final arrival time unless another rule above already determined a different reunion terminal/time. If multiple New Companions tie for earliest valid final arrival time and the reunion terminals are different, add the transfer editor flag `multiple new companions, manual confirmation required`.
--- IF the chosen New Companion's final leg of travel is a subway leg and no final arrival time is available:
* "Please communicate with your new companion to determine a meetup time in advance."
--- IF they will need to wait for their New Companion (if the final arrival time of their New Companion is greater than the time value in Arrival Time OR the final arrival time of their New Companion is greater than Departure Time of their Current Companion, check both Arrival Time and 2nd Arrival Time to determine the final arrival time of their New Companion):
* "Upon arrival, wait for your companion " + New Companion + " who will arrive at " + TIME (find the time that their New Companion will arrive and insert it here) + "."
--- IF they will NOT need to wait for their New Companion (if the final arrival time of their New companion is less than or equal to the time value in Arrival Time OR the final arrival time of their New companion is less than or equal to the Departure Time of their Current Companion, check both Arrival Time and 2nd Arrival Time to determine the final arrival time of their New Companion):
* "Upon arrival, your companion " + New Companion + " will be waiting for you."
--- IF the compared times are exactly equal:
* treat that as "your companion will be waiting for you."

/newline/

13. IF Second Leg? = "yes":
- The person has a second leg of travel. ONLY include the below information if Second Leg? = "yes"
- print("Second leg of travel:")

/newline/

14. IF 2nd Departure Terminal.contains("Subway"):
- remove the "Subway" text from the 2nd Departure Terminal value AND the 2nd Arrival Terminal value.
- print("Travel to " + 2nd Departure Terminal + " and ride the " + 2nd Departure Time + " to " + 2nd Arrival Terminal + ". Leave in time to arrive there at " + 2nd Arrival Time + ",  and meet your new companion, " + New Companion + ".")
- /newline/
ELSE:
- print("Departure Location: " + 2nd Departure Terminal)
- print("Departure Time: " + 2nd Departure Time)
/newline/
- print("Arrival Time: " + 2nd Arrival Time)
- print("Arrival Location: " + 2nd Arrival Location)
/newline/

15. print("Notes: " + NOTES)
- In the "Notes" portion, choose notes to include from the following list below. Choose instructions from the list based on whether the given conditions are met or not (possible instructions to be printed are marked at the beginning of the line with "*"):

-- IF there are multiple New Companions, use the earliest valid final arrival time unless another rule above already determined a different reunion terminal/time. If multiple New Companions tie for earliest valid final arrival time and the reunion terminals are different, add the transfer editor flag `multiple new companions, manual confirmation required`.
-- IF the chosen New Companion's final leg of travel is a subway leg and no final arrival time is available:
* "Please communicate with your new companion to determine a meetup time in advance."
-- IF they will NOT need to wait for their New Companion (if the final arrival time of their New Companion is less than or equal to the time value in 2nd Arrival Time OR the final arrival time of their New Companion is less than or equal to the Departure Time of their Current Companion, check both Arrival Time and 2nd Arrival Time to determine the final arrival time of their New Companion):
* "Your companion " + New Companion + " will be waiting for you."
-- IF they will need to wait for their New Companion (if the final arrival time of their New Companion is greater than the time value in 2nd Arrival Time OR the final arrival time of their New Companion is greater than the Departure Time of their Current Companion, check both Arrival Time and 2nd Arrival Time to determine the final arrival time of their New Companion):
* "Wait for your companion " + New Companion + " who will arrive at " + TIME (find the time that their New Companion will arrive and insert it here) + "."
-- IF the compared times are exactly equal:
* treat that as "your companion will be waiting for you."

16. Include the following characters at the end of each person's plan: ---------------

Preserve Hangul + UTF-8.

=== END FORMAT RULES ===

===OUTPUT RULES===

- Organize each person's list in the file by the zone they are currently in. Make a section for each zone. For example, everyone who is currently in the 경기 zone should be in a section with a header that looks like this:

---경기---

- In the final, completely formatted list, you MUST output each person's list immediately adjacent to that person's Current Companion. For example, the final list for each person's Current Companion MUST be located either directly above or directly below them in the final text. If there are three people in a companionship, they should all still be placed adjacent to each other.

- Each companionship's schedule block should have a header containing the name of their Current Area. This area header should only be at the top of the companionship, and not above each individual person. It should be in the following format: /newline/ + "------------------------- " + Current Area + " -------------------------". For example: 

/newline/
------------------------- 분당 E2 -------------------------

- IF there is an area that contains multiple companionships, those companionships should be adjacent together. Each companionship should still have its own area header. Most areas will have slightly different names, but if they both contain the same Korean name, they should be put adjacent to each other. For example, if one area header is labeled "분당 E2", and another is labeled "분당 E1", or "1 분당 E1", those should be placed adjacent to each other in the final list. If there are multiple of such occurrences, it does not matter which order they are placed in, as long as they are all near each other and in the same zone section.

===EXAMPLE OUTPUT===

---경기---

------------------------- 분당 E2 -------------------------

Justin Pugmire

Travel to 성남역 with Samuel Lockhart.

Departure Location: 성남역
Departure Time: 12:00

Arrival Time: 14:00
Arrival Location: 김제역

Notes: Upon arrival, wait for your companion Francis Galligao who will arrive at 14:20.

---------------

Samuel Lockhart

Drop off Justin Pugmire at 성남역. Wait at 성남역 until your new companion, Logan Hornberger, arrives there at 12:00.

---------------

------------------------- 2 분당 1 -------------------------

Francis Galligao

Travel to 대전역 with Trevon Wolfert.

Departure Location: 대전역
Departure Time: 10:00

Arrival Time: 14:20
Arrival Location: 수원역

Second leg of travel:

2nd Departure Location: 수원역
2nd Departure Time: 16:15

2nd Arrival Time: 17:40
2nd Arrival Location : 김제역

Notes: Your companion Justin Pugmire will be waiting for you.

---------------

Trevon Wolfert

Travel to 수지구청역 and ride the yellow line to 대전역. Leave in time to arrive there at 11:55, and meet your new companion, Alma Younger.

---------------
