# Machine Learning Classification Architecture

**Option C Implementation Plan**

## Overview

Transform Data Destroyer's classification system from regex-only to a hybrid ML approach that combines the precision of regex patterns with the recall and context-awareness of machine learning models.

## Goals

### Performance Targets
- **Precision**: 95%+ (minimize false positives)
- **Recall**: 90%+ (catch all sensitive data)
- **Speed**: < 2 seconds per document (1000 words)
- **False Positive Reduction**: 50% vs regex-only

### Features
- ✅ Hybrid regex + ML classification
- ✅ Context-aware entity recognition
- ✅ Active learning from user feedback
- ✅ Custom model training
- ✅ Multi-language support
- ✅ Model versioning and A/B testing

---

## Architecture

### High-Level Flow

```
Input Text
    ↓
┌───────────────────────────────────┐
│   Hybrid Classification Engine    │
├───────────────────────────────────┤
│                                   │
│  ┌─────────────┐  ┌────────────┐ │
│  │   Regex     │  │     ML     │ │
│  │  Patterns   │  │   Models   │ │
│  │  (High      │  │  (High     │ │
│  │  Precision) │  │  Recall)   │ │
│  └──────┬──────┘  └──────┬─────┘ │
│         │                │        │
│         └────────┬───────┘        │
│                  ↓                │
│         ┌─────────────────┐       │
│         │ Result Merger & │       │
│         │  Deduplicator   │       │
│         └────────┬────────┘       │
│                  ↓                │
└──────────────────┼────────────────┘
                   ↓
        Classification Results
        (with confidence scores)
                   ↓
        ┌──────────────────┐
        │ User Feedback    │
        │ (corrections)    │
        └────────┬─────────┘
                 ↓
        ┌──────────────────┐
        │ Active Learning  │
        │ (retrain models) │
        └──────────────────┘
```

### Tech Stack

**ML Frameworks:**
- **spaCy 3.7+** - NER for PII/PHI detection
- **transformers (HuggingFace)** - BERT-based models for context
- **scikit-learn** - Custom classifiers
- **torch** - Deep learning backend

**Infrastructure:**
- **Celery** - Async model training
- **Redis** - Task queue
- **MLflow** - Model versioning and tracking
- **PostgreSQL** - Training data storage

---

## Database Models

### 1. MLModel

Tracks trained models and their metadata.

```python
class MLModel(models.Model):
    """ML model registry"""

    # Model identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=50, choices=[
        ('spacy_ner', 'spaCy NER'),
        ('transformer', 'Transformer Model'),
        ('sklearn', 'Scikit-learn Classifier'),
        ('hybrid', 'Hybrid Model'),
    ])
    classification_types = models.JSONField(default=list)  # ['PII', 'PHI', etc.]

    # Model files
    model_path = models.CharField(max_length=500)
    config = models.JSONField(default=dict)

    # Performance metrics
    accuracy = models.FloatField(null=True)
    precision = models.FloatField(null=True)
    recall = models.FloatField(null=True)
    f1_score = models.FloatField(null=True)

    # Version control
    version = models.CharField(max_length=20)
    parent_model = models.ForeignKey('self', null=True, on_delete=models.SET_NULL)

    # Status
    is_active = models.BooleanField(default=False)
    is_production = models.BooleanField(default=False)

    # Timestamps
    trained_at = models.DateTimeField(auto_now_add=True)
    deployed_at = models.DateTimeField(null=True)

    # Training details
    training_samples = models.IntegerField(default=0)
    training_duration_seconds = models.FloatField(null=True)
    training_params = models.JSONField(default=dict)
```

### 2. TrainingDataset

Stores labeled examples for training.

```python
class TrainingDataset(models.Model):
    """Labeled training data for ML models"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    # Text and labels
    text = models.TextField()
    entities = models.JSONField(default=list)  # [{"start": 0, "end": 5, "label": "PII"}]
    classification_type = models.CharField(max_length=50)

    # Metadata
    source = models.CharField(max_length=50, choices=[
        ('user_feedback', 'User Feedback'),
        ('manual', 'Manual Annotation'),
        ('imported', 'Imported Dataset'),
        ('synthetic', 'Synthetic Data'),
    ])
    language = models.CharField(max_length=10, default='en')

    # Quality control
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    verified_at = models.DateTimeField(null=True)

    # Training usage
    used_in_training = models.BooleanField(default=False)
    last_used = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
```

### 3. ClassificationFeedback

User corrections for active learning.

```python
class ClassificationFeedback(models.Model):
    """User feedback on classification results"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    # Link to classification result
    classification_result = models.ForeignKey(ClassificationResult, on_delete=models.CASCADE)

    # Feedback
    is_correct = models.BooleanField()
    corrected_type = models.CharField(max_length=50, null=True)
    corrected_entities = models.JSONField(null=True)
    notes = models.TextField(blank=True)

    # User info
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Processing
    incorporated_in_training = models.BooleanField(default=False)
    training_batch = models.ForeignKey('TrainingBatch', null=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)
```

### 4. MLClassificationResult

Extended classification result with ML metadata.

```python
class MLClassificationResult(models.Model):
    """ML-specific classification results"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    # Link to base classification result
    classification_result = models.OneToOneField(ClassificationResult, on_delete=models.CASCADE)

    # ML model used
    model = models.ForeignKey(MLModel, on_delete=models.PROTECT)

    # Detailed results
    entities = models.JSONField(default=list)  # Detailed entity extraction
    regex_matches = models.JSONField(default=list)
    ml_matches = models.JSONField(default=list)

    # Confidence breakdown
    regex_confidence = models.FloatField()
    ml_confidence = models.FloatField()
    combined_confidence = models.FloatField()

    # Performance
    processing_time_ms = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)
```

### 5. TrainingBatch

Tracks model training runs.

```python
class TrainingBatch(models.Model):
    """Training batch tracking"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    # Model being trained
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE)

    # Training data
    training_samples = models.IntegerField()
    validation_samples = models.IntegerField()
    test_samples = models.IntegerField()

    # Results
    status = models.CharField(max_length=20, choices=[
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])

    # Metrics
    train_accuracy = models.FloatField(null=True)
    val_accuracy = models.FloatField(null=True)
    test_accuracy = models.FloatField(null=True)

    # Timing
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    duration_seconds = models.FloatField(null=True)

    # Logs
    logs = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
```

---

## ML Engine Components

### 1. Hybrid Classification Engine

```python
# discovery/ml/engine.py

class HybridClassificationEngine:
    """
    Combines regex patterns with ML models for optimal accuracy.
    """

    def __init__(self):
        self.regex_engine = RegexClassifier()
        self.ml_engine = MLClassifier()
        self.merger = ResultMerger()

    def classify(self, text: str, classification_types: List[str] = None) -> ClassificationResult:
        """
        Hybrid classification combining regex and ML.

        Args:
            text: Text to classify
            classification_types: Types to look for (PII, PHI, etc.)

        Returns:
            ClassificationResult with entities and confidence scores
        """
        # Run regex patterns (high precision)
        regex_results = self.regex_engine.classify(text, classification_types)

        # Run ML models (high recall)
        ml_results = self.ml_engine.classify(text, classification_types)

        # Merge and deduplicate
        combined_results = self.merger.merge(regex_results, ml_results)

        return combined_results
```

### 2. ML Classifier

```python
# discovery/ml/ml_classifier.py

class MLClassifier:
    """
    ML-based classification using spaCy and transformers.
    """

    def __init__(self):
        # Load models
        self.spacy_ner = self.load_spacy_model()
        self.medical_ner = self.load_medical_model()
        self.context_classifier = self.load_context_classifier()

    def classify(self, text: str, classification_types: List[str]) -> List[Entity]:
        """
        Classify using ML models.
        """
        entities = []

        # spaCy NER for general entities
        if 'PII' in classification_types:
            entities.extend(self.extract_pii(text))

        # Medical NER for PHI
        if 'PHI' in classification_types:
            entities.extend(self.extract_phi(text))

        # Context-aware classification
        entities = self.apply_context(text, entities)

        return entities

    def extract_pii(self, text: str) -> List[Entity]:
        """Extract PII using spaCy NER"""
        doc = self.spacy_ner(text)

        entities = []
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'DATE', 'MONEY']:
                entities.append(Entity(
                    text=ent.text,
                    start=ent.start_char,
                    end=ent.end_char,
                    label='PII',
                    sublabel=ent.label_,
                    confidence=self.calculate_confidence(ent),
                    source='spacy_ner'
                ))

        return entities
```

### 3. Active Learning Pipeline

```python
# discovery/ml/active_learning.py

class ActiveLearningPipeline:
    """
    Learn from user feedback to improve models.
    """

    def collect_feedback(self, classification_id: str, is_correct: bool, correction: dict):
        """
        Store user feedback for later training.
        """
        # Create training example from feedback
        training_example = self.create_training_example(
            classification_id,
            is_correct,
            correction
        )

        # Add to training dataset
        TrainingDataset.objects.create(**training_example)

    def trigger_retraining(self, model_id: str):
        """
        Trigger model retraining when enough feedback is collected.
        """
        # Check if we have enough new feedback
        feedback_count = ClassificationFeedback.objects.filter(
            incorporated_in_training=False
        ).count()

        if feedback_count >= RETRAIN_THRESHOLD:
            # Queue training job
            train_model.delay(model_id)

    def evaluate_improvement(self, old_model: MLModel, new_model: MLModel) -> bool:
        """
        Determine if new model is better than current model.
        """
        # Run on test set
        old_metrics = self.evaluate_model(old_model)
        new_metrics = self.evaluate_model(new_model)

        # Compare F1 scores
        return new_metrics['f1_score'] > old_metrics['f1_score']
```

### 4. Model Trainer

```python
# discovery/ml/trainer.py

class ModelTrainer:
    """
    Train and fine-tune ML models.
    """

    def train_spacy_ner(self, training_data: List[dict], epochs: int = 10):
        """
        Train spaCy NER model.
        """
        # Load blank model
        nlp = spacy.blank("en")
        ner = nlp.add_pipe("ner")

        # Add labels
        for example in training_data:
            for entity in example['entities']:
                ner.add_label(entity['label'])

        # Train
        optimizer = nlp.begin_training()

        for epoch in range(epochs):
            random.shuffle(training_data)
            losses = {}

            for batch in spacy.util.minibatch(training_data, size=8):
                for text, annotations in batch:
                    doc = nlp.make_doc(text)
                    example = Example.from_dict(doc, annotations)
                    nlp.update([example], sgd=optimizer, losses=losses)

            print(f"Epoch {epoch}: Loss {losses}")

        return nlp

    def fine_tune_transformer(self, model_name: str, training_data: List[dict]):
        """
        Fine-tune transformer model for classification.
        """
        # Load pre-trained model
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Prepare dataset
        dataset = self.prepare_dataset(training_data, tokenizer)

        # Training arguments
        training_args = TrainingArguments(
            output_dir="./models",
            num_train_epochs=3,
            per_device_train_batch_size=16,
            evaluation_strategy="epoch",
        )

        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset['train'],
            eval_dataset=dataset['validation'],
        )

        # Train
        trainer.train()

        return model
```

---

## API Endpoints

### ML Classification

```python
POST /api/discovery/ml/classify/
{
    "text": "John Smith's SSN is 123-45-6789",
    "classification_types": ["PII", "PHI"],
    "use_ml": true
}

Response:
{
    "entities": [
        {
            "text": "John Smith",
            "start": 0,
            "end": 10,
            "label": "PII",
            "sublabel": "PERSON",
            "confidence": 0.95,
            "source": "spacy_ner"
        },
        {
            "text": "123-45-6789",
            "start": 20,
            "end": 31,
            "label": "PII",
            "sublabel": "SSN",
            "confidence": 0.99,
            "source": "regex"
        }
    ],
    "overall_confidence": 0.97,
    "processing_time_ms": 145
}
```

### Feedback Submission

```python
POST /api/discovery/ml/feedback/
{
    "classification_id": "uuid",
    "is_correct": false,
    "corrected_type": "PII",
    "corrected_entities": [...],
    "notes": "This is actually not sensitive"
}
```

### Model Training

```python
POST /api/discovery/ml/train/
{
    "model_type": "spacy_ner",
    "classification_types": ["PII"],
    "use_feedback": true,
    "epochs": 10
}

Response:
{
    "batch_id": "uuid",
    "status": "queued",
    "estimated_duration_minutes": 15
}
```

### Model Metrics

```python
GET /api/discovery/ml/models/{id}/metrics/

Response:
{
    "model_id": "uuid",
    "accuracy": 0.94,
    "precision": 0.96,
    "recall": 0.92,
    "f1_score": 0.94,
    "confusion_matrix": [...],
    "sample_predictions": [...]
}
```

---

## Frontend Integration

### ML Classification UI

```typescript
// frontend/src/pages/MLClassification.tsx

function MLClassificationPage() {
  const [text, setText] = useState('')
  const [results, setResults] = useState(null)

  const classify = async () => {
    const response = await mlApi.classify(text, ['PII', 'PHI'])
    setResults(response)
  }

  return (
    <div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} />
      <button onClick={classify}>Classify with ML</button>

      {results && (
        <EntityHighlighter text={text} entities={results.entities} />
      )}
    </div>
  )
}
```

### Feedback Interface

```typescript
function FeedbackInterface({ result }) {
  const submitFeedback = async (isCorrect, correction) => {
    await mlApi.submitFeedback(result.id, isCorrect, correction)
  }

  return (
    <div>
      <p>Was this classification correct?</p>
      <button onClick={() => submitFeedback(true, null)}>Yes</button>
      <button onClick={() => openCorrectionModal()}>No, correct it</button>
    </div>
  )
}
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- [ ] Create database models
- [ ] Set up ML dependencies
- [ ] Implement basic spaCy NER
- [ ] Create hybrid engine structure

### Phase 2: Core ML (Weeks 3-4)
- [ ] Build hybrid classifier
- [ ] Implement confidence scoring
- [ ] Create API endpoints
- [ ] Add Celery for async tasks

### Phase 3: Active Learning (Weeks 5-6)
- [ ] Feedback collection system
- [ ] Training pipeline
- [ ] Model versioning
- [ ] A/B testing framework

### Phase 4: Frontend & Polish (Weeks 7-8)
- [ ] ML classification UI
- [ ] Feedback interface
- [ ] Performance dashboard
- [ ] Documentation
- [ ] Testing and optimization

---

## Success Metrics

### Quantitative
- Precision: 95%+
- Recall: 90%+
- F1 Score: 92%+
- Processing Speed: < 2s per document
- False Positive Reduction: 50% vs regex

### Qualitative
- User satisfaction with accuracy
- Reduced manual review time
- Better context understanding
- Multi-language support working

---

## Next Steps

1. **Create ML database models** in discovery app
2. **Set up dependencies** (spaCy, transformers)
3. **Implement basic classifier** with spaCy NER
4. **Build hybrid engine** combining regex + ML
5. **Create API endpoints** for classification
6. **Add Celery** for async training
7. **Build frontend UI** for ML features

Let's get started! 🚀
