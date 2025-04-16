# Feature Development Process

This rule defines the standard process for developing new features in our codebase.

## Core Principles

### 1. Single-Task Focus
- Work on exactly one task at a time
- Complete all requirements for a task before moving to the next
- Never implement multiple tasks in parallel
- Get explicit approval before starting each task
- Mark tasks as complete only when ALL requirements are met

### 2. Test-Driven Development
- Write tests BEFORE implementing functionality
- Run full test suite before and after each change
- All tests must pass before task completion
- Create/modify test cases for all code changes
- Test both happy path and edge cases
- No task is complete without corresponding test coverage

### 3. Requirements Clarity
- If requirements are unclear, ask questions before proceeding
- Break complex tasks into sub-tasks as the first step
  - Get approval for sub-task breakdown before implementation
- Don't make assumptions about requirements
- When discussing next steps, describe without implementing

### 4. Failure Management
- If stuck after 5 iterations, stop and seek advice
- Document attempted approaches and failures
- Focus on learning from failed attempts
- Use failures to improve documentation/process

### 5. Definition of Done
A task is only complete when:
- All tests are passing
- New tests added for new functionality
- Single task item fully implemented
- Code review feedback addressed
- Documentation updated if needed

### 6. Plan vs Implementation Separation
- Planning documents track WHAT needs to be done
- Implementation details belong in code/comments/PRs
- Keep plans focused on high-level requirements
- Avoid implementation specifics in planning docs

### 7. Task Workflow
1. Review current state and identify next task
2. Wait for explicit approval to proceed
3. Follow test-driven development process
4. Document any process improvements discovered

## Application

This process should be followed for all feature development work. It ensures:
- Consistent quality through test-driven development
- Clear communication and expectations
- Manageable, reviewable changes
- Learning from failures
- Proper documentation
- Maintainable codebase

## Exceptions

The process may be adjusted for:
- Critical hotfixes (but still require tests)
- Experimental prototypes (clearly marked as such)
- Documentation-only changes

In all cases, maintain the core principle of quality through testing. 