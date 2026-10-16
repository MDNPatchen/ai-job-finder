"""Offline tests for ranked resume evidence and full downloadable breakdowns."""
import ast
import copy
from collections import Counter
from pathlib import Path
import unittest

from ranked_breakdowns import (
    evidence_index, evidence_sort_key, breakdowns_json, breakdowns_csv_rows
)
from posting_metadata import reconcile_workplace_record
from job_workflow import preferences_allow
from government_feed_identity import dedupe_vacancy_urls, belongs_to_configured_agency
from employer_postings import posting_quality


def make_job(title="Operations Director", documented=0, confirmed=0, total=5,
             source="Greenhouse", company="Example Company", rank=10):
    return {
        "title":title, "company":company, "source":source,
        "url":"https://jobs.example.com/"+title.replace(" ","-"),
        "date":"2026-10-10", "location":"Rochester, MN",
        "work_style":"On-site", "remote":False,
        "description":"Business operations and leadership",
        "eligible":True,"government":False,"rank":rank,
        "qualification_match":{
            "resume_present":True,
            "label":"Some relevant resume evidence",
            "resume_matches":[{"area":"Area "+str(i), "listing_excerpt":"Job requested area "+str(i),
                               "resume_evidence":["Resume evidence "+str(i)]}
                              for i in range(documented)],
            "confirmed_only":[{"area":"Confirmed "+str(i),"listing_excerpt":"Job term "+str(i)}
                              for i in range(confirmed)],
            "not_documented":[{"area":"Not documented "+str(i),"listing_excerpt":"Job need "+str(i)}
                              for i in range(max(0,total-documented-confirmed))],
            "screeners":[{"type":"Education", "priority":"Possibly required — verify wording",
                          "listing_excerpt":"Bachelor's degree required",
                          "resume_status":"Not verified from resume"}],
            "total_areas":total,"resume_focus":"Explain documented skills."
        }
    }


def extracted_filter():
    code=Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    tree=ast.parse(code)
    target=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                and n.name=="filter_and_rank_jobs")
    target=copy.deepcopy(target)
    target.decorator_list=[]
    module=ast.fix_missing_locations(ast.Module(body=[target],type_ignores=[]))
    namespace={
        "Counter":Counter,
        "compile_resume_profile":lambda resume,areas: {"resume_present":bool(resume)},
        "verified_competencies":lambda:set(),
        "is_recent_posting":lambda j:True,
        "states_in_location":lambda location:["MN"],
        "normalized_key":lambda j:(j["title"],j["company"]),
        "evidence_sort_key":evidence_sort_key,
        "reconcile_workplace_record":reconcile_workplace_record,
        "preferences_allow":preferences_allow,
        "posting_quality":posting_quality,
        "dedupe_vacancy_urls":dedupe_vacancy_urls,
        "belongs_to_configured_agency":belongs_to_configured_agency,
        "GOVERNMENT_AGENCIES":[],
        "SCHOOLJOBS_AGENCIES":[],
        "score_job":lambda job,resume,query,profile:dict(job),
    }
    exec(compile(module,"app.py","exec"),namespace)
    return namespace["filter_and_rank_jobs"]


class RankedBreakdownTests(unittest.TestCase):
    def test_documented_resume_evidence_beats_unconfirmed(self):
        proven=make_job(documented=3,total=5)
        unconfirmed=make_job(confirmed=3,total=5)
        self.assertGreater(evidence_index(proven["qualification_match"]),
                           evidence_index(unconfirmed["qualification_match"]))

    def test_short_listing_does_not_appear_as_perfect_match(self):
        one=make_job(documented=1,total=1)
        self.assertEqual(evidence_index(one["qualification_match"]),20)

    def test_multiple_matched_requirements_score_above_single_skill(self):
        many=make_job(documented=5,total=6)
        single=make_job(documented=1,total=1)
        self.assertLess(evidence_sort_key(many),evidence_sort_key(single))

    def test_missing_resume_is_unassessed(self):
        q=make_job(documented=4)["qualification_match"]
        q["resume_present"]=False
        self.assertEqual(evidence_index(q),0)

    def test_untrusted_csv_fields_are_not_excel_formulas(self):
        fake=make_job(title='=HYPERLINK("https://evil.example")',documented=1)
        result=breakdowns_csv_rows([fake])
        self.assertTrue(result[0]['Job title'].startswith("'="))

    def test_csv_contains_rank_and_resume_quotes(self):
        rows=breakdowns_csv_rows([make_job(documented=2)])
        self.assertEqual(rows[0]["Rank"],1)
        self.assertEqual(rows[0]["Documented match count"],2)
        self.assertIn("Resume evidence 0",rows[0]["Actual resume excerpts"])
        self.assertIn("Bachelor",rows[0]["Education, license and experience checks"])

    def test_json_contains_all_breakdowns_in_ranking_order(self):
        jobs=[make_job(title="Best fit",documented=4,total=5),
              make_job(title="Less fit",documented=1,total=5)]
        reports=breakdowns_json(jobs)
        self.assertEqual([r["rank"] for r in reports],[1,2])
        self.assertEqual([r["job_title"] for r in reports],["Best fit","Less fit"])
        self.assertEqual(reports[0]["evidence_match_index"],80)
        self.assertTrue(reports[0]["formal_requirements_to_verify"])

    def test_filter_preserves_descending_order_across_sectors(self):
        jobs=[
            make_job(title="Low employer match",documented=1,total=5,rank=99),
            make_job(title="High government match",documented=5,total=6,source="NEOGOV",rank=7),
            make_job(title="Mid employer match",documented=3,total=5,rank=40)
        ]
        jobs[1]["government"]=True
        func=extracted_filter()
        result,_=func(jobs,None,"On-site + Hybrid","","uploaded resume text")
        self.assertEqual([r["title"] for r in result],
                         ["High government match","Mid employer match","Low employer match"])

    def test_full_results_include_all_qualified_jobs_from_same_employer(self):
        jobs=[make_job(title=f'Operations Director - District {i}',
                       company='Example Group',documented=5-i//3,
                       total=6,rank=20-i) for i in range(6)]
        func=extracted_filter()
        full, excluded=func(jobs,None,'On-site + Hybrid','','resume')
        self.assertEqual(len(full),6)
        self.assertEqual(excluded['employer_limit'],0)
        self.assertEqual([j['title'] for j in full],
                         [j['title'] for j in sorted(full,key=evidence_sort_key)])

    def test_compact_view_shows_three_and_counts_three_hidden(self):
        jobs=[make_job(title=f'Operations Director - District {i}',
                       company='Example Group',documented=5-i//3,
                       total=6,rank=20-i) for i in range(6)]
        limited, excluded=extracted_filter()(
            jobs,None,'On-site + Hybrid','','resume',3)
        self.assertEqual(len(limited),3)
        self.assertEqual(excluded['employer_limit'],3)
        self.assertEqual(limited[0]['title'],'Operations Director - District 0')

    def test_optional_compact_view_keeps_mayo_up_to_ten(self):
        jobs=[make_job(title=f'Operations Director - Unit {i}',
                       company='Mayo Clinic',source='Mayo Clinic',
                       documented=4,total=6) for i in range(11)]
        compact, excluded=extracted_filter()(
            jobs,None,'On-site + Hybrid','','resume',3)
        self.assertEqual(len(compact),10)
        self.assertEqual(excluded['employer_limit'],1)

    def test_distinct_requisition_urls_for_same_title_are_not_collapsed(self):
        from job_workflow import distinct_posting_key
        jobs=[make_job(title='Regional Operations Director',company='Example Media',
                       documented=4) for _ in range(3)]
        jobs[0]['location']='Phoenix, AZ'
        jobs[0]['url']='https://example.org/jobs/phoenix-101'
        jobs[1]['location']='Tucson, AZ'
        jobs[1]['url']='https://example.org/jobs/tucson-102'
        jobs[2]['location']='Phoenix, AZ'
        jobs[2]['url']='https://example.org/jobs/phoenix-103'
        unique={distinct_posting_key(j) for j in jobs}
        self.assertEqual(len(unique),3)

    def test_identical_direct_urls_ignore_tracking_query_parameters(self):
        from job_workflow import distinct_posting_key
        a=make_job(title='Regional Operations Director')
        b=dict(a)
        a['url']='https://example.org/jobs/123?utm_source=board'
        b['url']='https://example.org/jobs/123?utm_medium=alerts'
        self.assertEqual(distinct_posting_key(a),distinct_posting_key(b))

    def test_advanced_preferences_keep_unlisted_pay_by_default(self):
        job=make_job(title='Regional Operations Director')
        job['salary']=''
        results,excluded=extracted_filter()(
            [job],None,'On-site + Hybrid','','resume',None,
            {'minimum_salary':125000,'include_unlisted_salary':True})
        self.assertEqual(len(results),1)
        self.assertEqual(excluded['preferences'],0)

    def test_advanced_preferences_exclude_known_salary_below_threshold(self):
        job=make_job(title='Regional Operations Director')
        job['salary']='$80,000-$110,000 Annually'
        results,excluded=extracted_filter()(
            [job],None,'On-site + Hybrid','','resume',None,
            {'minimum_salary':125000,'include_unlisted_salary':True})
        self.assertEqual(len(results),0)
        self.assertEqual(excluded['preferences'],1)

    def test_recruiter_and_directory_links_are_hidden_by_default(self):
        direct=make_job(title='Director of Operations',company='Future Publishing')
        direct['url']='https://apply.workable.com/j/EC2A4EFE7C'
        recruiter=make_job(title='Vice President of Operations',
                           company='Keller Executive Search')
        recruiter['url']='https://apply.workable.com/j/DB19968E49'
        directory=make_job(title='Deputy City Manager',
                           company='City of New York',source='NYC Open Data')
        directory['url']='https://cityjobs.nyc.gov/jobs'
        filtered, excluded=extracted_filter()(
            [direct,recruiter,directory],None,'On-site + Hybrid','','resume')
        self.assertEqual([item['company'] for item in filtered],['Future Publishing'])
        self.assertEqual(excluded['recruiter'],1)
        self.assertEqual(excluded['directory_link'],1)

    def test_broader_listing_choice_requires_user_opt_in(self):
        direct=make_job(title='Director of Operations',company='Future Publishing')
        recruiter=make_job(title='Operations Director',
                           company='Keller Executive Search')
        directory=make_job(title='Deputy City Manager',
                           company='City of New York',source='NYC Open Data')
        directory['url']='https://cityjobs.nyc.gov/jobs'
        jobs=[direct,recruiter,directory]
        with_recruiter,_=extracted_filter()(
            jobs,None,'On-site + Hybrid','','resume',None,None,
            'Include recruiter listings with direct job links')
        self.assertEqual(len(with_recruiter),2)
        all_sources,_=extracted_filter()(
            jobs,None,'On-site + Hybrid','','resume',None,None,
            'All sources (including directory links)')
        self.assertEqual(len(all_sources),3)

    def test_explicit_canadian_location_is_excluded(self):
        Canadian=make_job(title='Director of Operations',
                          company='Some Publisher')
        Canadian['location']='Toronto, ON, CA'
        results,excluded=extracted_filter()(
            [Canadian],None,'On-site + Hybrid','','resume')
        self.assertEqual(results,[])
        self.assertEqual(excluded['foreign_location'],1)

    def test_no_resume_keeps_old_relevance_priority(self):
        jobs=[
            make_job(title="High evidence",documented=5,total=5,rank=3),
            make_job(title="High title match",documented=1,total=5,rank=30)
        ]
        func=extracted_filter()
        result,_=func(jobs,None,"On-site + Hybrid","","")
        self.assertEqual(result[0]["title"],"High title match")

    def test_mayo_remote_exception_preserved(self):
        mayo=make_job(title="Mayo remote director",documented=4,
                      source="Mayo Clinic",company="Mayo Clinic")
        mayo["work_style"]="Remote"
        others=make_job(title="Remote other director",documented=5,
                        source="Greenhouse",company="Other employer")
        others["work_style"]="Remote"
        result,_=extracted_filter()([others,mayo],None,"On-site + Hybrid","","resume")
        self.assertEqual([x["title"] for x in result],["Mayo remote director"])

    def test_old_and_undated_remain_excluded(self):
        func=extracted_filter()
        old=make_job(title="Undated vacancy",documented=5)
        old["date"]=""
        result,exclusion=func([old],None,"On-site + Hybrid","","resume")
        self.assertEqual(result,[])
        self.assertEqual(exclusion["undated"],1)


if __name__=="__main__":
    unittest.main()
