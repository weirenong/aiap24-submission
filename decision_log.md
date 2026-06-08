# AIAP Technical Assessment — Decision Log

**Candidate name (as in NRIC):** Ong Wei Ren

**Email (as used in your application):** weirenjune@gmail.com

---

## A note on this document

This decision log is the primary instrument by which we understand your thinking. The questions below cover the reasoning behind your work — from how you define the problem at the start to the decisions you made during the work itself. Do answer all five questions in your own words. 

You may use AI assistance freely on the technical deliverables (the EDA and the ML pipeline), but this Decision Log itself should be written by you — it is the record of your own thinking that we cross-check against your chat history.


---

## 1. Clarifying questions

What questions would you ask to better define and narrow the problem statement? For each question, briefly explain how the answer would meaningfully change your approach. 

Note: If it helps your decision-making, you may assume and list out the stakeholders' likely answers.


**Your answer:**

What is the key performance indicator here? It is assumed that the key performance indicator or metric the company is trying to improve is customaer statisfaction which is represented by the rating feature.

What would define running into trouble for deliveries, is a lower rating indicative that a delivery has run into trouble? If the head of operations is mainly concerned about lower ratings being deliveries with problems, we will focus on prediction of rating for deliveries. Similarly for the severity if lower ratings mean higher severity, we will assume the rating score also indicates how severe of an issue a particular delivery will be.

Is the main aim to highlight problematic deliveries so we can highlight to the drivers for their attention so it can be prioritised? The head of operations seems to want to highlight the issue to the drivers, so if we were to come up with a way to determine if a parcel or delivery is problematic, it can be used to complement a delivery assignment system where we will assign the delivery to the driver with the best predicted rating with each new delivery item that comes in.

Which type of delivery should we prioritise first? 2-hour, same-day or next-day delivery? As the timeframe for completion of the delivery is different, it may result in vastly different conditions required to fulfil each. Hence it is assumed that we will need to build models for each type separately. I will assume that the head of operations will want to handle the type that results in the higher number of low rating scores first and we will focus on that so we narrow the scope.

What is the threshold rating such that it is defined as a problematic delivery? If the CEO or Head of operations want to simply improve all ratings rather than eliminate all problematic deliveries, we can frame this as a regression issue. If they simply want to eliminate problematic deliveries below a certain threshold which is not our assumption, we will then use a classification system to predict this.

Is customer feedback important, how do we handle missing customer feedback? If the Head of operations finds that customer feedback is important, we will need to reclassify the feedback into broad categories so we can perform analysis on it. If there are alot of missing data and it is not always meaningful, we may omit this and opt to focus on other features for the prediction of the rating.

At what point or timing of the delivery lifecycle do we make the predition of the rating? Is it at booking or pickup? It is assumed that we will be doing this prediction before pickup so we will only include those that have fulfiled this condition. This is in line with the solution we are likely to propose which is to use the predicted rating to affect assignment of deliveries.

---

## 2. Defining the Problem Statement

Restate, in your own words, the refined problem you decided to solve. List your key assumptions. Briefly note what other framings you considered, and what you deliberately left out or scoped down, and why.


**Your answer:**

The objective is to predict the customer's rating score to help the company to assign deliveries to the best driver to achieve better overall ratings. We will build a model that predicts customer rating (1–5) for each delivery at booking time so this can be used for assignment to a driver. For every new delivery, the model will be used to score each available driver, predicting the expected rating if that driver handles the delivery. The dispatch team will then assign the delivery to the driver with the highest predicted rating. This solves the constraint where the company has to only make use of their current delivery fleet and still achieve better overall ratings.

Key Assumptions

Target Variable: Customer rating is the primary KPI representing delivery quality. Higher ratings = better delivery experience.

Prediction Timing: Predictions are made at booking time, before driver assignment and departure, using features available at that stage.

Driver Assignment Use Case: The model is used per-driver to rank candidates, not to flag existing deliveries. Each driver gets a predicted rating for a given delivery.

Available Drivers: The system assumes a pool of available drivers is known at the time of assignment. Driver-specific features (experience, vehicle type) will be included as inputs to the model.

Ratings is prioritised: The solution prioritises the best possible rating as opposed to fair or optimal fleet deployment. Capable drivers may receive more work than less capable ones.

---

## 3. Key decisions during Solution Development

Walk through three key decisions you made during Solution Development. For each: what options did you consider, what did you choose, and why? These can be technical (modelling choices, feature handling, evaluation metrics) or about the work itself (what to prioritise, what to drop, how to spend your time).


Decision 1: Treating the problem as multi-class classification instead of regression
The initial framing of predicting a 1–5 star rating could go either way, regression predicts a continuous score, classification predicts a discrete label. I tried Ridge Regression as a sanity check and it produced a validation R² of −1.235, meaning it performed worse than a dummy model that always predicts the mean. The reason is structural: a linear model tries to fit a straight line through a bounded, discrete scale, which compresses variance and pulls all predictions toward a central average. This means the model would almost never predict a 1 or 2 star rating, which is exactly the class we care most about from an operational standpoint, those are the problematic deliveries the head of operations wants to flag. Framing it as classification lets the model learn discrete decision boundaries for each rating class and lets us use macro-averaged metrics that give equal weight to the minority classes. So I pivoted fully to classification.

Decision 2: Handling class imbalance with a combination of under- and over-sampling on the training set only
The rating distribution is severely skewed: ratings 4 and 5 account for over 62,000 of the roughly 41,000 usable rows, while ratings 1, 2, and 3 each sit below 3,300. If I trained on the raw distribution, any reasonably capable model would just learn to predict 5 almost all the time and still hit reasonable accuracy, but it would be blind to the low-rating patterns the business actually wants to catch.
I considered three options: only over-sampling minorities, only under-sampling majorities, or a combination. Pure over-sampling on a dataset of this size would massively inflate the training set and risk overfitting on the duplicated minority rows. Pure under-sampling would throw away most of the majority class data and lose real signal. The combined approach, downsample ratings 4 and 5 to 4,000 each, then upsample ratings 1, 2, and 3 up to 4,000 each, strikes a balance: the training set ends up perfectly balanced at 20,000 rows without being either bloated or starved. Critically, I applied resampling only to the training set. The validation and test sets were kept at their natural distribution using stratified splitting so the evaluation reflects real-world class proportions and the metrics are not artificially inflated.

Decision 3: Feature selection based on bivariate analysis rather than including all engineered features
During feature engineering I created seven candidate features from the datetime columns: delivery hour, pickup hour, day of week, is weekend, is peak hour, driver daily total distance, driver median minutes to pickup, and minutes before late. Rather than feeding all of them into the model, I used the bivariate analysis, 100% normalised stacked bar charts of rating distribution per feature, to evaluate which ones actually shifted the rating mix.
Several features that seemed intuitively relevant turned out to show flat, uniform rating distributions: is_weekend, day_of_week, is_peak_hour. Weekend and weekday operations showed identical rating stacks; peak hour congestion appeared to be absorbed by drivers without affecting ratings. Including these would add noise without signal. Delivery hour and pickup hour, however, showed a clear pattern: deliveries after midnight (hours 0–3) had a pronounced spike in 1 and 2-star ratings. Rather than including the raw hour as a numeric feature, I collapsed it into a binary flag, delivery_hour_before_midnight and pickup_hour_before_midnight, to isolate that specific behavioural risk without giving the model a spurious numeric ordering across all 24 hours. Features like minutes_before_late and driver_daily_total_distance were also excluded because they require information not available at booking time, which would leak data from the future and make the model unusable in the actual assignment scenario.





---

## 4. Use of the AI assistant

Where did you use the AI assistant in this work? Give three specific examples of something the assistant suggested that you changed, rejected, or significantly modified — and explain your reasoning.


**Your answer:**
1. I used the AI assistant to brainstorm features. It gave me code that listed peak hours. As the list was too wide and covered too many hours in the day, 10 out of 24 hours. So I modified it to only capture the absolute peak periods which is 8-9am, 12-1pm and 6-8pm so the peak hours will result in more meaningful patterns. 

2. It also gave me features that used data that were are not going to be avaialble at the point of prediction like how late was the parcel, so I removed such suggested features to prevent data leakage.

3. The AI assitant gave me code that referenced the wrong df. So I manually edited them to reference the correct ones in my project.


---

## 5. Next Steps

If you had one more week to continue this project, what would you do next, and why? What signals from your current work make those the right next steps?

If I had one more week, I would focus primarily on improving the feature set, since the current performance ceiling (validation accuracy ~0.38, ROC AUC ~0.58) points to insufficient signal rather than a modelling problem, the architecture is sound, but the inputs are not expressive enough.

Build richer driver behaviour features. The single strongest predictor in the EDA was driver_experience_months (Spearman ρ = 0.22), but it is a coarse proxy for driver quality. With more time I would engineer per-driver historical features computed from past deliveries: rolling average rating over the last 30 and 90 days, recent variance in ratings (a driver with a declining trend matters differently from one who is consistently average), and the driver's historical performance broken down by route density bucket and distance band. These would capture current form rather than just tenure, and would slot naturally into the booking-time prediction workflow since they only require past data.

Engineer route-level contextual features. The EDA showed that num_stops_on_route (ρ = −0.10) and distance_km (ρ ≈ −0.08) both correlate with lower ratings, but the model currently sees each delivery in isolation. A driver handling their 8th stop of the day on a 40-stop route is in a meaningfully different situation than a driver on their first stop of the day. I would add a feature for the driver's accumulated stops and distance already completed that day at the time of the new booking. This is a feasible computation at assignment time since the dispatcher knows the current route state.
Use recipient_postal_code with an external map API. I dropped recipient_postal_code in this iteration to keep the implementation simple, but it holds real potential. Routing the postal code through a map API (e.g. OneMap or Google Maps Distance Matrix) would produce actual road distance and estimated travel time between the current driver location and the delivery address, a far more precise signal than the straight-line distance_km currently in the model. This directly addresses the distance_km correlation finding and is the most actionable data quality improvement available within the existing dataset.





---