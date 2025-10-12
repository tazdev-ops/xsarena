# Known Issues

## Runner Contract Issues

### Events Schema Inconsistencies
**Issue**: Some event types in events.jsonl may not follow the standard schema
**Status**: Under review
**Impact**: May affect monitoring and analysis tools
**Expected fix**: Standardize all event types to use consistent schema

**Standard Event Schema**:
```json
{
  "timestamp": "ISO8601 timestamp",
  "type": "event_type",
  "job_id": "job identifier",
  "stage": "current stage",
  "data": { ... additional data specific to event type }
}
```

**Standard Event Types**:
- `job_submitted`: Job creation
- `stage_started`: Stage execution begins
- `stage_completed`: Stage execution ends
- `section_written`: Content section saved
- `cost_update`: Cost/budget update
- `watchdog_timeout`: Stream timeout detected
- `retry_attempt`: Retry initiated
- `failover_trigger`: Backend failover occurred
- `aids_started`: Study aids generation begins
- `aids_completed`: Study aids generation ends
- `job_completed`: Job finished successfully
- `job_failed`: Job ended with error

## JobSpec Implementation Status

### CLI Flag Alignment
**Issue**: Some z2h flags may not be fully represented in JobSpec schema
**Status**: In progress
**Impact**: May require manual spec editing for advanced features
**Workaround**: Manually add missing fields to JobSpec YAML

## Monitoring & Observability

### Cost Tracking Granularity
**Issue**: Cost tracking may not be available at all stage levels
**Status**: Enhancement planned
**Impact**: Less granular budget monitoring

## Profile Support

### Profile Consistency
**Issue**: Style profiles (mastery/pedagogy/reference) may not be consistently applied across all stages
**Status**: Under review
**Impact**: Inconsistent output styling in multi-stage jobs

## Recommended Workarounds

For best results, use the JobSpec-first workflow and verify your specs contain all required parameters before execution.
