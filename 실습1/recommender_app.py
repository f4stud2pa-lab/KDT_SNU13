# -*- coding: utf-8 -*-
"""
AI응용 실습 문제 1: 초개인화 금융상품 추천 시스템 CLI 애플리케이션
사용자가 고객 ID(C01~C10)를 선택하여 리포트를 확인하고,
Minimal vs 초개인화 비교를 즉시 확인할 수 있는 실행 도구
"""

import sys
from data import CUSTOMER_PROFILES, GROUND_TRUTH
from evaluate import SIMULATION_RESULTS, calculate_summary_metrics

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def show_customer_list():
    print_header("고객 프로파일 샘플 목록 (10명)")
    print(f"{'ID':<5} | {'이름':<6} | {'나이/성별':<8} | {'직업':<14} | {'리스크':<8} | {'주요 목표'}")
    print("-" * 70)
    for c in CUSTOMER_PROFILES:
        print(f"{c['id']:<5} | {c['name']:<6} | {c['age']}세/{c['gender']:<2} | {c['job']:<14} | {c['risk_tolerance']:<8} | {c['primary_goal']}")

def display_comparison(customer_id):
    if customer_id not in SIMULATION_RESULTS:
        print(f"오류: 고객 ID '{customer_id}'를 찾을 수 없습니다.")
        return
    
    data = SIMULATION_RESULTS[customer_id]
    gt = data["ground_truth"]
    
    print_header(f"[{customer_id}] {data['name']} 고객 비교 분석 리포트")
    print(f"모범 정답 추천 상품: {', '.join(gt)}")
    
    print("\n" + "-" * 35 + " [1] Minimal 프롬프트 결과 " + "-" * 35)
    print(f"추천 상품: {', '.join(data['minimal']['recommended'])} (정답 일치율: {data['minimal']['accuracy_score']}%)")
    print(f"설명의 질 평가: {data['minimal']['eval_explanation']} / 5.0")
    print(f"고객 감성 평가: {data['minimal']['eval_emotion']} / 5.0")
    print(f"\n[생성된 리포트]\n{data['minimal']['sample_output']}")
    print(f"\n[주관 평가 코멘트]")
    print(f"- 설명의 질: {data['minimal']['eval_explanation_comment']}")
    print(f"- 감성 평가: {data['minimal']['eval_emotion_comment']}")
    
    print("\n" + "=" * 35 + " [2] 초개인화 프롬프트 결과 " + "=" * 35)
    print(f"추천 상품: {', '.join(data['hyper']['recommended'])} (정답 일치율: {data['hyper']['accuracy_score']}%)")
    print(f"설명의 질 평가: {data['hyper']['eval_explanation']} / 5.0")
    print(f"고객 감성 평가: {data['hyper']['eval_emotion']} / 5.0")
    print(f"\n[생성된 리포트]\n{data['hyper']['sample_output']}")
    print(f"\n[주관 평가 코멘트]")
    print(f"- 설명의 질: {data['hyper']['eval_explanation_comment']}")
    print(f"- 감성 평가: {data['hyper']['eval_emotion_comment']}")

def main():
    while True:
        print("\n" + "#" * 70)
        print("   AI응용 실습 1: 초개인화 금융상품 추천 시스템")
        print("#" * 70)
        print("1. 고객 목록 조회")
        print("2. 고객별 프롬프트 비교 리포트 보기 (C01 ~ C10)")
        print("3. 전체 10명 고객 비교 평가 요약 통계 보기")
        print("4. 종료")
        choice = input("\n메뉴 번호를 입력하세요: ").strip()
        
        if choice == "1":
            show_customer_list()
        elif choice == "2":
            show_customer_list()
            cid = input("\n조회할 고객 ID를 입력하세요 (예: C01, C03, C09): ").strip().upper()
            display_comparison(cid)
        elif choice == "3":
            summary = calculate_summary_metrics()
            print_header("전체 10명 고객 대상 정량 비교 평가 통계")
            print(f"{'평가 지표':<25} | {'Minimal 프롬프트':<20} | {'초개인화 프롬프트':<20}")
            print("-" * 70)
            print(f"{'모범답안 완전 일치율':<25} | {summary['minimal']['perfect_match_count']:<20} | {summary['hyper_personalized']['perfect_match_count']:<20}")
            print(f"{'평균 추천 정확도':<25} | {summary['minimal']['average_accuracy']:<20} | {summary['hyper_personalized']['average_accuracy']:<20}")
            print(f"{'설명의 질 평균 점수':<25} | {summary['minimal']['average_explanation_score']:<20} | {summary['hyper_personalized']['average_explanation_score']:<20}")
            print(f"{'고객 감성 평가 평균 점수':<25} | {summary['minimal']['average_emotion_score']:<20} | {summary['hyper_personalized']['average_emotion_score']:<20}")
        elif choice == "4" or choice.lower() == "exit" or choice.lower() == "q":
            print("프로그램을 종료합니다.")
            break
        else:
            print("올바른 번호를 입력해 주세요.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cid = sys.argv[1].upper()
        display_comparison(cid)
    else:
        # CLI 인자가 없으면 바로 통계 출력
        summary = calculate_summary_metrics()
        print("실행 인자 없음. 요약 통계 자동 출력:")
        print(summary)
