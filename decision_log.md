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

We will build a model that predicts customer rating (1–5) for each delivery at booking time. For every new delivery, the model will be used to score each available driver, predicting the expected rating if that driver handles the delivery. The dispatch team will then assign the delivery to the driver with the highest predicted rating.

Key Assumptions

Target Variable: Customer rating is the primary KPI representing delivery quality. Higher ratings = better delivery experience.

Prediction Timing: Predictions are made at booking time, before driver assignment and departure, using features available at that stage.

Driver Assignment Use Case: The model is used per-driver to rank candidates, not to flag existing deliveries. Each driver gets a predicted rating for a given delivery.

Available Drivers: The system assumes a pool of available drivers is known at the time of assignment. Driver-specific features (experience, vehicle type) will be included as inputs to the model.

---

## 3. Key decisions during Solution Development

Walk through three key decisions you made during Solution Development. For each: what options did you consider, what did you choose, and why? These can be technical (modelling choices, feature handling, evaluation metrics) or about the work itself (what to prioritise, what to drop, how to spend your time).


**Your answer:**





---

## 4. Use of the AI assistant

Where did you use the AI assistant in this work? Give three specific examples of something the assistant suggested that you changed, rejected, or significantly modified — and explain your reasoning.


**Your answer:**





---

## 5. Next Steps

If you had one more week to continue this project, what would you do next, and why? What signals from your current work make those the right next steps?


**Your answer:**





---