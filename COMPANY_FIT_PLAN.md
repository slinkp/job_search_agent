# Automatic Company Fit Decision Implementation Plan

This plan outlines the steps needed to implement automated decision-making about whether a company is a good fit, while learning ML engineering practices through hands-on experience.

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
- [x] Rate company data for training, validation, and test data
  - [x] This should be a process where the user is presented with company data and asked to rate them good/bad/need more info. Do this via a script, not cursor chat
  - [x] The output should be captured as suitable training data for the model, eg in CSV format
  - [x] Start with existing ~30 companies in our google spreadsheet, for initial dataset
  - [x] Do initial training on this data to vet the code works. Don't expect accuracy yet.
  - [ ] Generate synthetic training data:
    - [x] Implement RandomCompanyGenerator:
        - [x] Random probabilities with realistic distribution
    - [x] Implement LLMCompanyGenerator:
        - [x] Create prompt for LLM to generate diverse company profiles
        - [x] Add error handling and validation
        - [x] Add synthetic data markers in company_id
    - [ ] Implement HybridCompanyGenerator:
        - [ ] Use random generation for numeric fields
        - [ ] Use LLM for text fields and correlations
        - [ ] Implement business rules for realism
    - [ ] Generate initial test batch:
        - [ ] Generate ~20 companies using each generator type
        - [ ] Use rate_companies.py to validate quality
        - [ ] Compare quality between generator types
        - [ ] Select best performing generator
    - [ ] Generate full dataset:
        - [ ] Generate ~100 companies using chosen generator
        - [ ] Use rate_companies.py to rate all companies
        - [ ] Verify distribution matches real data
        - [ ] Use existing train/val/test split functionality

### 2. Build Initial ML Pipeline
- [x] Choose a framework for building the ML classifier.
  - [x] Compare and contrast the pros and cons of various libraries eg fastai.
- [x] Set up ML training infrastructure:
  - [x] Create data preprocessing pipeline
  - [x] Implement Random Forest classifier
  - [x] Add cross-validation
  - [ ] Set up model persistence
- [ ] Train initial model:
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
  - [ ] Feature importance breakdown - where would this belong?
  - [ ] Similar companies comparison **this is probably overkill**
- [ ] Add manual rating input for overriding (and so we can improve future training)
- [ ] Add tests for new UI components

### 7. Add Monitoring and Analytics
- [ ] Track prediction accuracy over time
- [ ] Monitor feature importance changes
- [ ] Track synthetic vs real data performance
- [ ] Add periodic model performance reports

### 8. Documentation
- [ ] Document ML pipeline in README, just an overview
- [ ] Document retraining procedures
- [ ] Document feature engineering process
- [ ] Document model performance metrics

### Considerations
- Start simple with one feature, add complexity only when needed
- Use synthetic data carefully, watching for any biases it might introduce
- Monitor real vs synthetic data performance separately
- Keep manual override option always available
- Consider periodically retraining on only real data as more becomes available 


### Result notes on LLM synthetic data generation

Example calls like
```
time python company_classifier/generate_synthetic_data.py \
  --generator llm --num-companies 10 \
  --model gpt-4-0125-preview  --output-dir data/synthetic/llm-gpt-4-0125-preview
```
gpt-4-turbo-preview: 8.7 sec / company
Nearly all types were "private unicorn", one "private"
Filled out compensation amounts, pretty narrow range (220k-270k)
All remote_policy were some hybrid variation
Eng size 150-500.
Total size 500-1200
Nearly all headquarters SF.  Most NYC addresses "350 5th ave".
Ai notes were extensive but pretty similar

gpt-4-0125-preview: 8.8 sec / company
Names repeated
8 private unicorn, 2 private, no public or finance
Comp 220k-275k
All hybrid
eng size 150-500
total size 450-1200
HQ either SF or empty
NY address mostly 350 5th Ave
AI notes decent, farily similar

gpt-3-5-turbo:  1.9 sec / company
ALL types were "private"
Total comp range 180k-220k
All remote some variation of hybrid
Eng size 120-150
Total size 400-5000
All headquarters SF
NY addresses mix of midtown, "main street brooklyn", wall st
AI notes short but reasonable
