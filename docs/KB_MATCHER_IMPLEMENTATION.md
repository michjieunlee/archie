# KBMatcher Implementation

## Overview

The KBMatcher component has been fully implemented with structured output (Pydantic models) and template-based content formatting. It uses a value-addition-first approach to determine whether new content should CREATE, UPDATE, or IGNORE KB documents.

## Core Principle

**VALUE ADDITION OVER TOPIC SIMILARITY**

Even if two topics are not highly similar, new content should UPDATE an existing document if it provides:
- Supporting information, examples, or edge cases
- Latest updates or recent findings
- Complementary details (different angle on same problem)
- Follow-up resolution to previously documented issues
- Temporal context ("We tried X, here's what we learned")

## Key Features

### 1. Structured Output with Pydantic Models

Uses LangChain's `with_structured_output()` for type-safe LLM responses:

```python
class MatchResult(BaseModel):
    action: MatchAction  # CREATE, UPDATE, or IGNORE
    confidence_score: float  # 0.0-1.0
    reasoning: str
    value_addition_assessment: str
    
    # Unified fields for both UPDATE and CREATE
    document_path: Optional[str]  # Path of document (matched for UPDATE, suggested for CREATE)
    document_title: Optional[str]  # Title of document
    category: Optional[str]  # One of: troubleshooting, process, decision, reference, or general
```

**Note:** The current implementation uses **unified fields** (`document_path`, `document_title`, `category`) instead of separate fields for UPDATE and CREATE actions.

**Benefits:**
- No manual JSON parsing or error handling
- Type-safe, validated output
- Direct Pydantic model from LLM
- Simpler field structure

### 2. Template-Based Content Formatting

Content is formatted according to category-specific templates:

**Troubleshooting Template:**
```
Problem Description → Environment → Symptoms → Root Cause → Solution → Prevention
```

**Processes Template:**
```
Overview → Prerequisites → Steps → Validation → Troubleshooting
```

**Decisions Template:**
```
Context → Decision → Rationale → Alternatives → Consequences → Implementation
```

This ensures consistency with the actual templates in `.archie/templates/`.

### 3. Value-Addition-First Matching Strategy

Decision logic prioritizes value addition:

```python
if adds_value_to_existing:
    return UPDATE  # Even if topics are not highly similar
elif is_independent_and_valuable:
    return CREATE
else:
    return IGNORE
```

**UPDATE criteria:**
1. Provides supporting information
2. Contains latest updates
3. Offers complementary details
4. Resolves follow-ups
5. Adds temporal context

**CREATE criteria:**
1. Truly independent topic
2. Different problem domain
3. Substantial standalone value
4. Would clutter existing document if merged

**IGNORE criteria:**
1. Pure duplicate
2. Insufficient detail
3. Low AI confidence (< 0.6)
4. Not knowledge-worthy

## Implementation Details

### KBMatcher Class (`app/ai_core/matching/kb_matcher.py`)

**Main Method:**
```python
async def match(
    self,
    kb_document: KBDocument,
    existing_kb_docs: Optional[List[Dict[str, Any]]] = None,
) -> MatchResult
```

The `match()` method:
1. Checks AI confidence (low confidence may recommend IGNORE)
2. Returns CREATE if no existing docs found
3. Finds potentially relevant documents using `_find_relevant_documents()`
4. Uses LLM with structured output via `_llm_match_decision_structured()`
5. Falls back to CREATE on errors

**Key Supporting Methods:**

- `_find_relevant_documents()`: Pre-filters documents using heuristics (category matching, tag overlap)
- `_llm_match_decision_structured()`: Uses LLM with structured output to make the final decision
- `_format_new_content_by_category()`: Formats KB document content according to category template
- `_format_existing_docs()`: Formats existing docs for LLM prompt
- `_create_result()`: Helper to create CREATE action result

### LLM Chain with Structured Output

```python
# Build prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", MATCHING_SYSTEM_PROMPT),
    ("human", "New content and existing docs...")
])

# Create chain with structured output
chain = prompt | self.llm.with_structured_output(MatchResult)

# Invoke and get Pydantic model directly
result = await chain.ainvoke(data)  # Returns MatchResult
```

### Content Formatting by Category

The `_format_new_content_by_category()` method formats extracted content according to category templates:

```python
def _format_new_content_by_category(self, kb_document: KBDocument) -> str:
    extraction = kb_document.extraction_output
    category = kb_document.category.value
    
    if category == "troubleshooting":
        return f"""### Problem Description
{extraction.problem_description}

### Environment
- **System**: {extraction.system_info}
- **Version**: {extraction.version_info}
- **Environment**: {extraction.environment}

### Symptoms
{extraction.symptoms}

### Root Cause
{extraction.root_cause}

### Solution
{extraction.solution_steps}

### Prevention
{extraction.prevention_measures}

### Related Issues
{extraction.related_links or 'None'}"""
    # ... similar for processes and decisions
```

### GitHub Integration

The matcher works with GitHub repository data through the `read_kb_repository()` method:

**Expected KB Document Structure:**
```python
{
    "title": "Document Title",
    "path": "category/filename.md",  # Note: uses 'path' field
    "category": "troubleshooting",  # One of: troubleshooting, process, decision, reference, or general
    "tags": ["tag1", "tag2"],
    "content": "Full markdown content with frontmatter",
    "markdown_content": "Content without frontmatter",
    "frontmatter": {...}
}
```

The matcher reads from `existing_kb_docs` provided by the GitHub client's `read_kb_repository()` method.

## Integration with KB Orchestrator

The KBMatcher is integrated into `KBOrchestrator` (`app/services/kb_orchestrator.py`):

```python
# Fetch existing KB documents from GitHub repository
try:
    all_kb_docs = await self.github_client.read_kb_repository()
    # Filter by category for more focused matching
    existing_kb_docs = [
        doc for doc in all_kb_docs 
        if doc.get("category") == kb_document.category.value
    ]
except Exception as e:
    logger.warning(f"Failed to fetch KB documents: {e}")
    existing_kb_docs = []

# Match against existing KB
match_result = await self.matcher.match(kb_document, existing_kb_docs)
```

**Orchestrator Flow:**
1. Extract information from thread
2. Mask PII
3. **Match against existing KB entries** ← KBMatcher integration
4. Generate KB document based on match result
5. Create GitHub PR (future implementation)

## Configuration

### Environment Variables
Required in `.env`:
- `OPENAI_MODEL`: Model to use (configured in app settings, e.g., "gpt-5")

### Matching Parameters
- **AI confidence check**: Documents with `ai_confidence < 0.6` may be recommended for IGNORE
- **Temperature**: Set to 0.0 for deterministic matching decisions  
- **Categories**: Supports all 5 categories (troubleshooting, process, decision, reference, general)
- **Model**: Configured via `config.py` - uses SAP GenAI Hub proxy (no API key needed)

## Usage Example

```python
# Initialize matcher
matcher = KBMatcher()

# Fetch existing KB documents from GitHub
all_kb_docs = await github_client.read_kb_repository()
existing_kb_docs = [
    doc for doc in all_kb_docs 
    if doc.get("category") == kb_document.category.value
]

# Match with structured output
match_result = await matcher.match(kb_document, existing_kb_docs)

# Use the result
if match_result.action == MatchAction.UPDATE:
    file_path = match_result.document_path
    title = match_result.document_title
    logger.info(f"UPDATE: {title} at {file_path}")
    
elif match_result.action == MatchAction.CREATE:
    file_path = match_result.document_path
    category = match_result.category
    logger.info(f"CREATE: New document at {file_path}")
    
else:  # IGNORE
    logger.info(f"IGNORE: {match_result.reasoning}")

# Always available
logger.info(f"Confidence: {match_result.confidence_score}")
logger.info(f"Value assessment: {match_result.value_addition_assessment}")
```

## Files Modified

1. **app/ai_core/matching/kb_matcher.py**
   - Full implementation with structured output
   - Template-based content formatting
   - Value-addition-first decision logic

2. **app/ai_core/prompts/matching.py**
   - MATCHING_SYSTEM_PROMPT with value-addition criteria
   - Documents MatchResult structure for LLM

3. **app/integrations/github/client.py**
   - `read_kb_repository()` - Reads KB documents from GitHub
   - Returns documents with `path`, `title`, `category`, `tags`, and content fields

4. **app/services/kb_orchestrator.py**
   - Fetches existing KB documents before matching
   - Filters by category for focused matching
   - Handles errors with empty list fallback

5. **app/ai_core/matching/__init__.py**
   - Exports MatchResult and MatchAction

6. **app/ai_core/prompts/__init__.py**
   - Exports MATCHING_SYSTEM_PROMPT

## Testing

The implementation includes comprehensive tests in `tests/integrations/test_kb_matcher.py`:

1. **Mock KB documents** - Sample documents across all categories
2. **Heuristic pre-filtering** - Category and tag-based filtering
3. **LLM-based assessment** - Structured output with Pydantic validation
4. **Error handling** - Fallback to CREATE on LLM failures
5. **Async/await patterns** - Proper async implementation throughout
6. **Real GitHub integration** - Tests with actual GitHub repository (optional)

**Test Scenarios:**
- CREATE new document when no similar documents exist
- UPDATE existing document when relevant match found
- IGNORE low quality content (low AI confidence)
- Empty repository handling
- All category types (troubleshooting, process, decision, reference, general)
- Value addition assessment

## Decision Examples

### Example 1: Different Topic → UPDATE

**Existing**: "Database Connection Timeout Issues"
- Focus: Connection pool exhaustion, timeout configuration

**New**: "Memory Leak Causing Database Connection Issues"  
- Focus: Memory leak after 4 hours leading to connection failures

**Decision**: **UPDATE** existing document
- **Reason**: Identifies additional root cause for connection problems
- **Value**: Enhances troubleshooting with new failure mode
- **Merge**: Add to "Root Cause" section

### Example 2: Similar Topic → CREATE

**Existing**: "PostgreSQL Connection Pool Configuration"
- Focus: How to configure connection pools

**New**: "PostgreSQL Query Performance Optimization"
- Focus: Optimizing slow queries with indexes

**Decision**: **CREATE** new document
- **Reason**: Different aspect of PostgreSQL management
- **Value**: Substantial standalone content
- **Search**: Different user intents

### Example 3: Latest Update → UPDATE

**Existing**: "Staging Deployment Process" (3 months old)
- Steps: 5-step deployment process

**New**: "New Security Approval Step Required (Jan 2026)"
- Content: Security team approval now mandatory

**Decision**: **UPDATE** existing document
- **Reason**: Latest information on same process
- **Value**: Keeps process documentation current
- **Merge**: Insert as new step, update validation

## Error Handling

The matcher includes robust error handling:
- **No existing docs**: Returns CREATE action automatically
- **Empty relevant documents**: Returns CREATE action
- **LLM failures**: Falls back to CREATE with low confidence and error reason
- **GitHub fetch failures**: Orchestrator catches and uses empty list

## Next Steps for Production

1. **Implement embedding-based similarity** for faster pre-filtering
2. **Add caching layer** for frequently accessed documents
3. **Track metrics**:
   - Action distribution (CREATE/UPDATE/IGNORE percentages)
   - Confidence score distribution
   - LLM response times
   - User override rates
4. **Implement feedback loop** to improve matching over time
5. **Add confidence threshold parameter** to filter results
6. **Implement hybrid search** (semantic + keyword) for better pre-filtering