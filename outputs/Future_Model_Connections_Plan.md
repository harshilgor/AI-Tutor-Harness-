# Future Model Connections Plan

**Status:** Deferred. This is not part of the current Learn, Ask, and Quiz implementation scope.

## Product decision

Forma should eventually let a learner choose how model-powered features are supplied, without making model access a prerequisite for the local learning workspace.

Consumer ChatGPT subscriptions and Claude.ai subscriptions must not be used as a substitute for API access. Their chat subscriptions and developer API billing are separate products. Forma must not ask for provider website credentials, browser sessions, or cookies, and must not automate a provider's consumer chat website.

The supported paths will be:

1. A first-party API key from OpenAI, Anthropic, Google, or another supported provider.
2. An OpenRouter API key for access to its available model catalog.
3. A local model endpoint such as Ollama or LM Studio, with no cloud key.
4. The built-in deterministic local experience when no model is configured.

## Model Settings user experience

Model Settings belongs in **Workspace Settings** in the desktop application. It should be a short, guided flow rather than a raw configuration form.

### 1. Select a connection

Show provider cards for OpenAI, Anthropic, OpenRouter, Google AI, and Local model. Each card explains where processing occurs, how billing works, and whether an API key is needed.

Do not describe a ChatGPT Plus/Pro, Claude Pro/Max, or other consumer chat subscription as compatible model access. Explain that users need the provider's developer/API account if they want that provider's models.

### 2. Add credentials or a local endpoint

For a cloud provider, request only its API key. For a local runtime, request a loopback endpoint and perform no internet call.

The desktop main process stores credentials in the operating system encrypted credential store. The renderer never receives persisted secrets, backups never contain them, and diagnostics/logs must redact them. A key can be removed at any time.

### 3. Choose a compatible model

List only models that satisfy Forma's current capability requirements: reliable structured output, sufficient context, and appropriate availability for the selected account. The list should show a simple cost class, context limit, and capability badges.

OpenRouter may load a filtered catalog. Native providers should initially expose a maintained, tested allow-list. Do not present a model as supported merely because its identifier can be entered.

### 4. Validate before activation

The **Test connection** action sends a minimal structured-output request through the local tutor service. It verifies the credential, selected model, structured response contract, and a safe request budget before the connection becomes active.

Errors should say what the learner can do next: key rejected, billing/credits unavailable, model unavailable, rate limited, endpoint unreachable, or unsupported response format.

### 5. Set learner defaults

Let the learner set a default model for Ask and Learn. A later iteration may permit separate defaults for quiz drafting and low-stakes recommendations, but final assessment qualification remains provider-independent.

The chat composer can offer a session-level model override. It should state the active model and keep the setting visible while a session is active.

### 6. Privacy and spend controls

Before the first use, explain what data is sent to the selected provider: the learner's prompt and only material or notes they explicitly attach as context. Display a per-request output cap and an estimated cost class; later, add optional monthly and per-session budgets.

## Technical architecture

Keep existing teaching policy, learner-state logic, assessment quality gates, and provider transport separate.

```
Ask / Learn / Quiz workflow
          |
          v
Teaching policy + assessment qualification (provider-independent)
          |
          v
ModelProvider interface
  |       |        |        |
OpenAI Anthropic OpenRouter Local runtime
```

The provider boundary should expose structured completion, model capability metadata, a health/validation call, and normalized error codes. Provider adapters must not decide mastery, source support, quiz acceptance, or learner progression.

Model selection should be represented by a non-secret local profile: provider ID, model ID, endpoint identifier when relevant, capability version, and user preferences. The associated secret remains in the credential store and is referenced by a stable credential name only.

## Phased delivery when this work is scheduled

1. Finish and evaluate the current Learn, Ask, and Quiz workflows first.
2. Add a provider-neutral settings domain and provider profile persistence without changing teaching logic.
3. Complete direct OpenAI and OpenRouter configuration, validation, and model selection.
4. Add Anthropic and a local Ollama endpoint adapter using the same contracts.
5. Add provider catalog refresh, capability filtering, privacy disclosure, and spend controls.
6. Add per-session overrides and complete desktop integration tests for secret storage, restart behavior, provider failure, and removal.

## Acceptance criteria

- A user can add, test, select, replace, and remove a supported connection without exposing its key in the UI, backup, logs, or browser storage.
- Unsupported models cannot be activated for structured learning output.
- Learn, Ask, and Quiz retain their policy and quality behavior when the selected provider changes.
- The local deterministic experience works with no connection configured.
- Provider failures create actionable messages and do not lose learner work.
- Automated tests cover provider selection, secret isolation, connection validation, normalized failures, model fallback, and backup exclusion.

## Current priority

Do not implement this plan while the current learning workflows need work. The present product priority is to improve the teaching quality, grounded context handling, assessment generation, evaluation, and interaction design of **Learn**, **Ask**, and **Quiz**.
