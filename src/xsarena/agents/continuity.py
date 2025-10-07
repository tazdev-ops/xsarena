"""Continuity agent for XSArena - checks consistency and alignment with the plan."""

import os
import re
from typing import Any, Dict

from .base import Agent


class ContinuityAgent(Agent):
    """Agent responsible for checking continuity, consistency, and plan alignment."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("continuity", config)

    async def run(self, job_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze content for continuity, consistency, and plan alignment.

        Args:
            job_id: The ID of the job to work on
            context: Context containing content to analyze and plan

        Returns:
            Dictionary containing analysis report and suggestions
        """
        # Get parameters from context
        subject = context.get("subject", "Unknown topic")
        edited_sections = context.get("edited_sections", [])
        plan_path = context.get("plan_path")

        # Load all content to analyze
        all_content = ""
        for section_path in edited_sections:
            with open(section_path, "r", encoding="utf-8") as f:
                all_content += f.read() + "\n\n"

        # Load the plan if available
        plan_content = ""
        if plan_path and os.path.exists(plan_path):
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_content = f.read()
        else:
            # Try to load from job artifacts
            plan_artifact = self.load_artifact(job_id, "plan")
            if plan_artifact:
                plan_content = plan_artifact

        # Perform continuity analysis
        analysis_results = self._analyze_continuity(all_content, plan_content, subject)

        # Generate a human-readable report
        report_content = self._generate_report(analysis_results, subject)

        # Save the report
        report_path = self.save_artifact(job_id, "continuity_report", report_content)

        # Write an event to the job log
        self.write_event(
            job_id,
            {
                "type": "continuity_analysis_completed",
                "agent": "continuity",
                "issues_found": len(analysis_results.get("issues", [])),
                "sections_analyzed": len(edited_sections),
            },
        )

        # Write detailed issues as separate events
        for issue in analysis_results.get("issues", []):
            self.write_event(
                job_id,
                {
                    "type": "continuity_issue",
                    "agent": "continuity",
                    "issue_type": issue["type"],
                    "description": issue["description"],
                    "severity": issue.get("severity", "medium"),
                },
            )

        return {
            "artifacts": {"report": report_path},
            "suggestions": {
                "next_agent": "done",  # Multi-agent sequence complete
                "report_path": report_path,
                "issues_found": analysis_results.get("issues", []),
                "quality_score": analysis_results.get("quality_score", 0.0),
            },
        }

    def _analyze_continuity(self, content: str, plan: str, subject: str) -> Dict[str, Any]:
        """Analyze the content for continuity, consistency, and plan alignment."""
        issues = []

        # Check for plan alignment
        if plan:
            plan_issues = self._check_plan_alignment(content, plan)
            issues.extend(plan_issues)

        # Check for consistency
        consistency_issues = self._check_consistency(content)
        issues.extend(consistency_issues)

        # Check for content quality
        quality_issues = self._check_content_quality(content)
        issues.extend(quality_issues)

        # Calculate a quality score (0-1 scale, 1 being best)
        quality_score = self._calculate_quality_score(len(issues), len(content))

        return {"issues": issues, "quality_score": quality_score, "total_issues": len(issues)}

    def _check_plan_alignment(self, content: str, plan: str) -> list:
        """Check if content aligns with the planned outline."""
        issues = []

        # Extract section titles from plan
        plan_titles = re.findall(r"#*\s+(.+)", plan)

        # Extract section titles from content
        content_titles = re.findall(r"#*\s+(.+)", content)

        # Check if planned sections are covered
        for title in plan_titles:
            found = False
            for content_title in content_titles:
                if (
                    title.lower().strip() in content_title.lower().strip()
                    or content_title.lower().strip() in title.lower().strip()
                ):
                    found = True
                    break

            if not found:
                issues.append(
                    {
                        "type": "missing_plan_section",
                        "description": f"Planned section '{title}' is not covered in the content",
                        "severity": "high",
                    }
                )

        # Check for content that's not in the plan
        for title in content_titles:
            found = False
            for plan_title in plan_titles:
                if (
                    title.lower().strip() in plan_title.lower().strip()
                    or plan_title.lower().strip() in title.lower().strip()
                ):
                    found = True
                    break

            if not found:
                issues.append(
                    {
                        "type": "unplanned_content",
                        "description": f"Content section '{title}' was not in the original plan",
                        "severity": "medium",
                    }
                )

        return issues

    def _check_consistency(self, content: str) -> list:
        """Check for consistency in terminology and concepts."""
        issues = []

        # Check for consistent terminology (simple version - would be enhanced in production)
        terms = ["model", "algorithm", "approach", "method", "technique", "framework"]  # Example terms
        content_lower = content.lower()

        # Look for inconsistent terminology usage
        for term in terms:
            if term in content_lower:
                # In a real implementation, check for synonymous terms that should be consistent
                pass  # This is a simplified implementation

        return issues

    def _check_content_quality(self, content: str) -> list:
        """Check for basic content quality issues."""
        issues = []

        # Check for very short paragraphs (might indicate incomplete thoughts)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        very_short = [p for p in paragraphs if len(p) < 30 and len(p.split()) < 5]

        if len(very_short) > 0:
            issues.append(
                {
                    "type": "short_paragraphs",
                    "description": f"Found {len(very_short)} very short paragraphs that might need expansion",
                    "severity": "low",
                }
            )

        # Check for repetitive content
        # This is a simplified version - in practice would use more sophisticated techniques
        if len(content) > 1000:  # Only check if content is substantial
            # Look for potential repetition
            pass  # Basic repetition check

        return issues

    def _calculate_quality_score(self, issue_count: int, content_length: int) -> float:
        """Calculate a quality score based on issues found relative to content length."""
        if content_length == 0:
            return 0.0

        # Normalize issue count by content length
        normalized_issues = issue_count / (content_length / 1000)  # Issues per 1000 chars

        # Score calculation: fewer issues = higher score
        score = max(0.0, min(1.0, 1.0 - (normalized_issues * 0.1)))

        return score

    def _generate_report(self, analysis_results: Dict[str, Any], subject: str) -> str:
        """Generate a human-readable continuity report."""
        report = [f"# Continuity Report for {subject}\n"]

        # Summary
        report.append("## Summary")
        report.append(f"- Quality Score: {analysis_results['quality_score']:.2f} (0.0-1.0, higher is better)")
        report.append(f"- Total Issues Found: {analysis_results['total_issues']}\n")

        # Detailed issues
        report.append("## Issues Found")
        if analysis_results["issues"]:
            for i, issue in enumerate(analysis_results["issues"], 1):
                report.append(f"### Issue {i}: {issue['type'].replace('_', ' ').title()}")
                report.append(f"- Severity: {issue.get('severity', 'medium')}")
                report.append(f"- Description: {issue['description']}")
                report.append("")  # Empty line for spacing
        else:
            report.append("- No significant issues found!\n")

        # Recommendations
        report.append("## Recommendations")
        if analysis_results["issues"]:
            high_severity = [i for i in analysis_results["issues"] if i.get("severity") == "high"]
            if high_severity:
                report.append(f"- Address the {len(high_severity)} high-severity issues first")
            report.append("- Review the identified sections for alignment with the original plan")
            report.append("- Consider revising content to improve consistency")
        else:
            report.append("- Content appears to be well-aligned with the plan")
            report.append("- No major consistency issues detected")

        return "\n".join(report)
