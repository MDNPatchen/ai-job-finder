"""Deduplicate scoring cautions for the *same* missing specialist experience.

Do not conflate a degree with work experience, an internal-only restriction
with career stage, or unrelated professional requirements. Preserve every
employer-stated excerpt for human verification, but count the strongest
caution in one overlapping domain once in the comparative fit calculation.
The index is not an eligibility verdict.
"""

# Explicit labels prevent fuzzy keyword overlaps from incorrectly merging
# independent disciplines (e.g. finance vs accounting; construction vs HVAC).
_EXPERIENCE_GROUPS={
    "Construction / engineering operations":"construction-experience",
    "Construction project / preconstruction leadership":"construction-experience",
    "Construction / preconstruction delivery experience":"construction-experience",
    "Dedicated corporate finance / investment analysis":"corporate-finance-experience",
    "Corporate finance / FP&A specialization":"corporate-finance-experience",
    "Dedicated social media strategy / campaigns":"social-media-experience",
    "Dedicated social media campaign leadership":"social-media-experience",
    "Music rights and licensing clearances":"music-licensing-experience",
    "Music licensing / copyright clearances":"music-licensing-experience",
    "Industrial environmental health & safety specialization":"ehs-experience",
    "Environmental health and safety / OSHA":"ehs-experience",
    "Professional UX / product design":"ux-design-experience",
    "Product / UX design portfolio":"ux-design-experience",
    "Equity compensation and total rewards specialty":"equity-admin-experience",
    "Compensation and equity administration":"equity-admin-experience",
    "Laboratory science / mass spectrometry":"lab-science-experience",
    "Analytical laboratory mass spectrometry":"lab-science-experience",
    "IT technical project delivery":"it-project-experience",
    "IT-specific project delivery":"it-project-experience",
    "Marketing science / statistical analysis":"marketing-science-experience",
    "Advanced marketing science / statistical modeling":"marketing-science-experience",
}
_SOURCE_PRIORITY={"domain":0,"career":1,"posting":2}


def calibrate_cautions(specialties, career_findings, posting_checks):
    """Calculate effective deductions while retaining all raw cautions.

    The highest single penalty wins in each explicitly equivalent *experience*
    group; all other requirements are scored separately. Postings win ties
    over title-based guesses. Formal education, licensure, residency and
    application restrictions never share an experience group.
    """
    sources={
        "domain":[dict(c) for c in (specialties or [])],
        "career":[dict(c) for c in (career_findings or [])],
        "posting":[dict(c) for c in (posting_checks or [])],
    }
    candidates=[]
    for source,items in sources.items():
        for index,item in enumerate(items):
            raw=max(0,int(item.get("ranking_caution") or 0))
            item["applied_ranking_caution"]=raw
            family=_EXPERIENCE_GROUPS.get(item.get("area"))
            if source=="posting" and item.get("type")!="Field-specific experience":
                family=None
            if raw and family:
                candidates.append((family,raw,_SOURCE_PRIORITY[source],source,index))

    winners={}
    for family,points,priority,source,index in candidates:
        # Employer minimum qualifications take precedence over inferred
        # title/domain caution even when their suggested point amounts differ.
        suggestion=(priority,points,source,index)
        if family not in winners or suggestion[:2]>winners[family][:2]:
            winners[family]=suggestion
    for family,_points,_priority,source,index in candidates:
        if (source,index)!=(winners[family][2],winners[family][3]):
            sources[source][index]["applied_ranking_caution"]=0
            sources[source][index]["covered_by"]=family

    domain=min(38,sum(x["applied_ranking_caution"] for x in sources["domain"]))
    career=min(42,sum(x["applied_ranking_caution"] for x in sources["career"]))
    posting=min(65,sum(x["applied_ranking_caution"] for x in sources["posting"]))
    raw=(min(38,sum(int(x.get("ranking_caution") or 0) for x in sources["domain"]))+
         min(42,sum(int(x.get("ranking_caution") or 0) for x in sources["career"]))+
         min(65,sum(int(x.get("ranking_caution") or 0) for x in sources["posting"])))
    applied=domain+career+posting

    return {
        "specialties":sources["domain"],
        "career_cautions":sources["career"],
        "posting_checks":sources["posting"],
        "domain_penalty":domain,
        "career_penalty":career,
        "posting_penalty":posting,
        "overlap_relief":max(0,raw-applied),
        "adjustment_note":(
            "Overlapping field-experience cautions counted once; "
            "degree, license and eligibility requirements remain separate."
            if raw>applied else
            "No overlapping professional-experience deductions."
        ),
        "specialist_gap":any(
            int(item.get("ranking_caution") or 0)>0
            for items in sources.values() for item in items
            if (_EXPERIENCE_GROUPS.get(item.get("area")) and
                (items is not sources["posting"] or
                 item.get("type")=="Field-specific experience"))
        ),
    }
