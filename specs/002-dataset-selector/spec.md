# Feature Specification: Dataset Selector

**Feature Branch**: `002-dataset-selector`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "On the ./data/datasets/ folder, I put a sample dataset called orcamentos-aeb-csv. On the ./data/briefing folder, that is a orcamentos-aeb-csv.md file that describes it's structure. We need to create a module that will have the responsibility of selecting and returning the correct dataset for the agent to answer the question the user asked. In the future, we will have thousands of datasets, and a complex logic to select them (probably with subagents and RAG), but for now I just want our single sample dataset to always be returned. It should also be considered that in the future the datasets won't be stored locally, only the briefings. The datasets will be downloaded on-demand. But for now, we can consider that the briefing file name is the key of the dataset, and can always be mapped to a dataset in the ./data/datasets/ folder."

## Clarifications

### Session 2026-09-18

- Q: Should this feature also record each dataset-selection decision as usage/research data, or is that logging left for a separate, later feature? → A: In scope — this feature MUST log each dataset selection decision (question, dataset key, timestamp) as part of its own requirements.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Obtain the dataset needed to answer a question (Priority: P1)

The question-answering agent receives a question from a user and needs to know which dataset to consult and where to find it, along with a description of that dataset's structure, so it can query the right data and produce a correct answer.

**Why this priority**: This is the entire purpose of the feature. Without it, the agent has no mechanism for discovering which data to use when answering a question.

**Independent Test**: Can be fully tested by submitting a dataset selection request (with any user question as input) and verifying the response identifies the `orcamentos-aeb-csv` dataset, includes its briefing, and points to the location of its data files.

**Acceptance Scenarios**:

1. **Given** a user question about federal budget execution for AEB or MCTIC, **When** the agent requests a dataset for that question, **Then** the system returns the `orcamentos-aeb-csv` dataset's briefing and the location of its data files.
2. **Given** a user question unrelated to any topic covered by the available data (e.g., a question about weather), **When** the agent requests a dataset for that question, **Then** the system still returns the `orcamentos-aeb-csv` dataset, since relevance matching across datasets is not implemented in this phase and it is the only dataset registered.

---

### User Story 2 - Locate a dataset's files from its briefing key (Priority: P2)

Given a dataset briefing's file name, the module resolves that name to the location of the corresponding dataset's data files, so that the pairing between "description of the data" and "the data itself" is consistent and predictable as more datasets are added later.

**Why this priority**: This establishes the naming/lookup convention the rest of the system (and future, more sophisticated selection logic) will depend on. Getting this mapping right now avoids rework when more datasets are introduced.

**Independent Test**: Can be fully tested by taking the known briefing file name `orcamentos-aeb-csv` and verifying it resolves to the `orcamentos-aeb-csv` folder under the datasets directory.

**Acceptance Scenarios**:

1. **Given** the briefing file `orcamentos-aeb-csv.md`, **When** the module resolves its dataset key, **Then** it returns the location of the `orcamentos-aeb-csv` folder in the datasets directory.

---

### Edge Cases

- What happens when the user's question has no relation to the content of any available dataset? The system still returns the single available dataset, since no relevance-matching or "no match found" logic exists in this phase.
- What happens if a dataset's key (briefing file name) does not correspond to an existing folder in the datasets directory? The system MUST surface a clear error rather than returning a broken or empty location, so the caller does not silently proceed with missing data.
- What happens when more than one briefing/dataset pair exists in the future? Selecting among them is explicitly out of scope for this feature; this feature only guarantees correct, consistent behavior for the single dataset that exists today.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST provide a way for the agent to request the dataset needed to answer a given user question.
- **FR-002**: System MUST respond to every such request with a dataset selection result that includes (a) the dataset's briefing (its structural description) and (b) the location of the dataset's data files.
- **FR-003**: System MUST always select and return the `orcamentos-aeb-csv` dataset, since it is the only dataset currently registered, regardless of the content of the user's question.
- **FR-004**: System MUST use a dataset briefing's file name as the unique key identifying that dataset, and MUST use that same key to locate the dataset's data files within the datasets directory.
- **FR-005**: System MUST report a clear error when a dataset's key does not correspond to an existing folder in the datasets directory, instead of returning an incomplete or invalid result.
- **FR-006**: System MUST return a result for any user question submitted, including questions unrelated to the available dataset's subject matter, since determining relevance is not part of this feature's scope.
- **FR-007**: System MUST record each dataset selection decision as usage data, capturing at least the user's question, the selected dataset's key, and a timestamp, so that dataset selection outcomes are available for later research analysis.

### Key Entities

- **Dataset Briefing**: A document describing a dataset's structure, fields, coverage, and limitations. Its file name is the unique key that identifies the dataset it describes.
- **Dataset**: The underlying data files that can be queried to answer a question. Stored in a location determined by its briefing's key.
- **Dataset Selection Result**: The response returned to the agent for a given question, pairing a dataset's briefing with the location of its data files.
- **Dataset Selection Log Entry**: A recorded observation of a single dataset selection decision, capturing the user's question, the selected dataset's key, and the timestamp of the decision.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: 100% of dataset selection requests receive a response containing both a dataset's briefing and the location of its data files.
- **SC-002**: A requester can determine which dataset was selected directly from the response, without needing prior knowledge of internal storage layout.
- **SC-003**: 100% of returned dataset locations point to a folder that actually contains the dataset's data files (no responses reference a missing or nonexistent location).
- **SC-004**: The single-dataset behavior defined here requires no change to how the agent issues a request when additional datasets and more sophisticated selection logic are introduced later — only the internal selection outcome changes.
- **SC-005**: 100% of dataset selection requests produce a corresponding recorded log entry capturing the question, the selected dataset's key, and a timestamp.

## Assumptions

- Only one dataset, `orcamentos-aeb-csv`, exists at this time. It is always returned for every request, since there is nothing yet to select among.
- The briefing file name (without its extension) is treated as the dataset's canonical key, and is assumed to always match the name of a folder under the datasets directory today.
- Datasets are currently stored locally in full under the datasets directory. A future change will keep only briefings stored locally and download full datasets on demand — that on-demand retrieval behavior is out of scope for this feature, which assumes the data files are already present locally when selected.
- Future growth to thousands of datasets, with more sophisticated selection logic (e.g., subagents, retrieval-augmented matching), is explicitly out of scope for this feature. This feature only needs to establish the always-return-the-one-dataset behavior and the briefing-name-as-key convention that future logic will build on.
