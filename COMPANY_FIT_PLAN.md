# Automatic Company Fit Decision Implementation Plan

This plan outlines the steps needed to implement automated decision-making about whether a company is a good fit, while learning ML engineering practices through hands-on experience.

## Working Process
When implementing this plan, follow these rules strictly:

1. **One Task at a Time**
   - Work on exactly one checkbox item at a time
   - After completing a single item, stop and ask for next steps
   - Never check multiple boxes in one go
   - A task is NOT complete until ALL its test requirements are met
   - Wait for explicit permission before implementing any task, even if you know what the next step is
   - When a task is complete, explicitly mark its checkbox with [x]
   - Only mark a checkbox when ALL its sub-checkboxes (if any) are complete

2. **Test-Driven Development**
   - Write tests BEFORE implementing functionality
   - Run all tests with the command `./test` before and after each change
   - All tests must pass before moving to next item
   - Create or modify test cases for any code changes
   - Test both happy path and edge cases
   - No checkbox can be marked complete without corresponding test coverage

3. **Clarity First**
   - If a task is unclear, ask questions before proceeding
   - Complex items should be broken into sub-steps as the first action
     - In that case, ask for approval of the new steps before proceeding
   - Don't make assumptions about requirements
   - When asked about next steps, only describe them - do not implement without explicit instruction

4. **Handle Failures Gracefully**
   - If you can't get code working after 5 iterations, stop
   - Ask for advice before continuing further
   - Document what you've tried and what failed

5. **Definition of Done**
   - All tests passing
   - New tests added for new functionality
   - Single checkbox item completed
   - Ready to proceed to the next item after asking permission to do so

6. **Plan vs Implementation**
   - This plan document tracks WHAT needs to be done, not HOW
   - Implementation details, technical issues, and coding challenges should be handled in the code/comments/PRs
   - Only modify this plan to clarify requirements or adjust the high-level steps
   - Never add implementation-specific notes or debugging information to the plan

7. **Task Flow**
   1. Review current state and identify next task
   2. Wait for explicit instruction to proceed
   3. If instructed to proceed, follow test-driven development process
   4. If only asked about next steps, provide description without implementation

## Primary Goals
1. Automate the process of identifying good-fit companies to save time and maintain consistency
2. Learn practical ML engineering through building a real-world pipeline:
   - Working with small, imbalanced datasets
   - Combining real and synthetic training data
   - Feature engineering and incremental improvement
   - Model monitoring and maintenance
3. Create a system that can evolve as more real-world data becomes available

## ML Approach Comparison

### Random Forest (Selected Approach)
Pros:
- Works well with small datasets (30-150 samples)
- Handles missing data naturally
- Mix of numerical and categorical features is fine
- Built-in feature importance analysis
- Resistant to outliers
- No feature scaling needed
- Good balance of simplicity and power
Cons:
- Less powerful than deep learning (but that's irrelevant for our data size)
- Can overfit with too many trees
- Model size grows with number of trees

### Logistic Regression
Pros:
- Simplest possible approach
- Very interpretable (direct feature weights)
- Fast training and prediction
- Small model size
Cons:
- Assumes linear relationships
- Needs feature scaling
- Sensitive to outliers
- Manual feature engineering needed
- Less powerful for complex patterns

### Support Vector Machine (SVM)
Pros:
- Can capture non-linear patterns with kernels
- Works well with medium-sized datasets
- Good with high-dimensional data
Cons:
- Requires careful feature scaling
- Less interpretable than Random Forest
- Kernel selection can be tricky
- Slower training with non-linear kernels

### Neural Network
Pros:
- Can learn very complex patterns
- Flexible architecture
- Could incorporate text features directly
Cons:
- Overkill for our small dataset
- Requires much more data (1000s of samples)
- More complex to implement and maintain
- Less interpretable
- Requires careful architecture design
- Needs GPU for efficient training

### Decision Tree (Single)
Pros:
- Simplest tree-based approach
- Most interpretable
- No preprocessing needed
Cons:
- Tends to overfit
- Less stable than Random Forest
- Lower accuracy in practice
- Sensitive to small data changes

Random Forest gives us the best balance for our goals:
1. Learning ML engineering (good complexity/benefit ratio)
2. Small dataset handling
3. Interpretability
4. Future extensibility
5. Reasonable implementation effort

## Technical Approach
We'll use a Random Forest classifier as our learning vehicle, starting with compensation data and incrementally adding features as we validate the approach. This classifier was chosen because:
- Works well with small datasets
- Handles mixed numerical/categorical features
- Provides feature importance analysis
- Relatively interpretable
- Good introduction to ML pipelines

## Implementation Steps

### 1. Initial Data Collection and Preparation
- [x] Create schema for storing company fit decisions:
  - [x] Write tests for company fit decision schema:
    - [x] Test serialization/deserialization of fit fields
    - [x] Test validation of fit category values
    - [x] Test confidence score range validation
    - [x] Test timestamp handling
    - [x] Test features list handling
  - [x] Implement schema in Company model:
    - [x] Categorize a company/role as good, bad, or more information needed
    - [x] Confidence score
    - [x] Timestamp of decision
    - [x] Features used in decision
    - [x] Store in database as a blob on the Company model
  - [x] All tests must pass before marking complete
- [ ] Rate company data for training, validation, and test data
  - [ ] This should be a process where the user is presented with company data and asked to rate them good/bad/need more info. Do this via a script, not cursor chat
  - [ ] The output should be captured as suitable training data for the model, eg in CSV format
  - [ ] Start with existing ~30 companies in our google spreadsheet, for initial dataset
  - [ ] Do initial training on this data to vet the code works. Don't expect accuracy yet.
  - [ ] Generate synthetic training data:
    - [ ] Create prompt for LLM to generate diverse company profiles
    - [ ] Generate ~100 synthetic companies with varying attributes
    - [ ] Have the user review and categorize synthetic companies using the same process as for the real data.
    - [ ] Store synthetic data with clear marking as synthetic
  - [ ] Train the model
    - [ ] Iteratively refine until we decide it's accurate enough
### 2. Build Initial ML Pipeline (Single Feature)
- [ ] Choose a framework for building the ML classifier.
  - [ ] Compare and contrast the pros and cons of various options eg fastai.
- [ ] Set up ML training infrastructure:
  - [ ] Create data preprocessing pipeline
  - [ ] Implement Random Forest classifier
  - [ ] Add cross-validation
  - [ ] Set up model persistence
- [ ] Train initial model using only compensation data:
  - [ ] Extract compensation features (base, stock, bonus)
  - [ ] Train on combined real + synthetic data
  - [ ] Evaluate performance using cross-validation
  - [ ] Analyze feature importance
- [ ] Add basic prediction endpoint
- [ ] Add confidence scoring
- [ ] Add tests for ML pipeline

### 3. Validation and Iteration (Single Feature)
- [ ] Create validation dashboard:
  - [ ] Show prediction vs actual for known companies
  - [ ] Display confidence scores
  - [ ] Show feature importance
- [ ] Collect feedback on initial predictions
- [ ] Tune model parameters if needed
- [ ] Document initial performance metrics

### 4. Expand Feature Set Incrementally
- [ ] Add role-level features:
  - [ ] AI/ML focus score
  - [ ] Level/seniority indicators
  - [ ] Retrain and validate
- [ ] Add company environment features:
  - [ ] Remote work compatibility
  - [ ] Work/life balance indicators
  - [ ] Ability to stay in NYC/Brooklyn
  - [ ] Retrain and validate
- [ ] Add mission alignment features:
  - [ ] Social impact indicators
  - [ ] Technology focus
  - [ ] Retrain and validate
- [ ] Document performance changes with each feature addition

### 5. Integrate with Existing Flow
- [ ] Update company research task to include fit prediction
      by calling the predictor in the existing "is_good_fit" function.
- [ ] Add manual override capability:
  - [ ] Store overrides for future training
  - [ ] Track override reasons
- [ ] Add retraining triggers:
  - [ ] After N new labeled examples
  - [ ] After manual overrides
  - [ ] On demand
  - [ ] Integrate output into our google spreadsheet format.
### 6. Enhance UI
- [ ] Add fit prediction display to company list:
  - [ ] Prediction (good/bad fit/more info needed)
  - [ ] Confidence score
  - [ ] Most influential features
- [ ] Add detailed prediction view:
  - [ ] Feature importance breakdown
  - [ ] Similar companies comparison **this is probably overkill**
- [ ] Add manual rating input for new training data
- [ ] Add tests for new UI components

### 7. Add Monitoring and Analytics
- [ ] Track prediction accuracy over time
- [ ] Monitor feature importance changes
- [ ] Track synthetic vs real data performance
- [ ] Add periodic model performance reports

### 8. Documentation
- [ ] Document ML pipeline in README, just an overview
- [ ] Document feature engineering process
- [ ] Document model performance metrics
- [ ] Document retraining procedures

### Considerations
- Start simple with one feature, add complexity only when needed
- Use synthetic data carefully, watching for any biases it might introduce
- Monitor real vs synthetic data performance separately
- Keep manual override option always available
- Consider periodically retraining on only real data as more becomes available 