#!/usr/bin/env python3
"""
Twitter Controversy Analyzer
Searches a Twitter/X profile for tweets containing controversial keywords
and analyzes them using AI to identify controversial content.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict
import tweepy
from dotenv import load_dotenv

from analyzer import TwitterSearcher
from extractor import ControversyAnalyzer
from keywords import CONTROVERSIAL_KEYWORDS

load_dotenv()


def load_api_keys():
    """load api keys from environment variables."""
    twitter_bearer_token = os.getenv("X_BEARER_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not twitter_bearer_token:
        print("error: X_BEARER_TOKEN environment variable not set")
        sys.exit(1)
    if not openai_api_key:
        print("error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    return twitter_bearer_token, openai_api_key


def analyze_profile(username: str, twitter_searcher: TwitterSearcher, 
                   analyzer: ControversyAnalyzer) -> Dict:
    """
    analyze a twitter profile for controversial tweets.
    args:
        username: twitter username (without @)
        twitter_searcher: twittersearcher instance
        analyzer: controversyanalyzer instance
    returns:
        dictionary with analysis results
    """
    print(f"{'*'*60}")
    print(f"analyzing profile: @{username}")
    print(f"{'*'*60}\n")
    
    # validate user exists
    if not twitter_searcher.validate_user(username):
        print(f"error: user '@{username}' not found or account is private.")
        sys.exit(1)
    
    all_results = []
    controversial_tweets = []
    
    print(f"searching for tweets containing {len(CONTROVERSIAL_KEYWORDS)} controversial keywords using batch search...\n")
    
    # batch search for all keywords at once using OR operators
    try:
        tweets = twitter_searcher.search_tweets_by_keywords_batch(username, CONTROVERSIAL_KEYWORDS)
    except tweepy.BadRequest:
        # query might be too long, fall back to individual searches
        print("batch query failed (possibly too long), falling back to individual keyword searches...\n")
        tweets = []
        for idx, keyword in enumerate(CONTROVERSIAL_KEYWORDS, 1):
            print(f"[{idx}/{len(CONTROVERSIAL_KEYWORDS)}] searching for keyword: '{keyword}'...", end=" ", flush=True)
            keyword_tweets = twitter_searcher.search_tweets_by_keyword(username, keyword)
            # add matched_keywords field for consistency
            for tweet in keyword_tweets:
                tweet['matched_keywords'] = [keyword]
            tweets.extend(keyword_tweets)
            print(f"found {len(keyword_tweets)} tweet(s)")
    
    total_tweets_found = len(tweets)
    
    print(f"\nfound {total_tweets_found} total tweet(s) matching keywords\n")
    
    # track analyzed tweet IDs to avoid duplicate analysis
    analyzed_tweet_ids = set()
    
    # analyze each tweet
    for idx, tweet in enumerate(tweets, 1):
        tweet_id = tweet['id']
        
        # skip if already analyzed (shouldn't happen with batch search, but safe guard)
        if tweet_id in analyzed_tweet_ids:
            continue
        
        analyzed_tweet_ids.add(tweet_id)
        
        matched_keywords = tweet.get('matched_keywords', [])
        keyword_display = ', '.join(matched_keywords) if matched_keywords else 'unknown'
        
        print(f"[{idx}/{total_tweets_found}] analyzing tweet id: {tweet_id} (keywords: {keyword_display})...", end=" ", flush=True)
        analysis = analyzer.analyze_controversy(tweet['text'])
        
        # create result for each matched keyword (for backward compatibility with reporting)
        for keyword in matched_keywords:
            result = {
                'tweet_id': tweet_id,
                'text': tweet['text'],
                'created_at': tweet['created_at'],
                'keyword': keyword,
                'matched_keywords': matched_keywords,  # include all matched keywords
                'public_metrics': tweet['public_metrics'],
                'analysis': analysis
            }
            
            all_results.append(result)
        
        # add to controversial tweets only once per tweet (deduplicated)
        if analysis['is_controversial']:
            # use first matched keyword for the controversial tweet entry
            primary_keyword = matched_keywords[0] if matched_keywords else 'unknown'
            controversial_result = {
                'tweet_id': tweet_id,
                'text': tweet['text'],
                'created_at': tweet['created_at'],
                'keyword': primary_keyword,
                'matched_keywords': matched_keywords,
                'public_metrics': tweet['public_metrics'],
                'analysis': analysis
            }
            controversial_tweets.append(controversial_result)
            print(f"CONTROVERSIAL (score: {analysis['controversy_score']}/10)")
        else:
            print(f"not controversial (score: {analysis['controversy_score']}/10)")
        
        # if no keywords matched (shouldn't happen, but handle gracefully)
        if not matched_keywords:
            result = {
                'tweet_id': tweet_id,
                'text': tweet['text'],
                'created_at': tweet['created_at'],
                'keyword': 'unknown',
                'matched_keywords': [],
                'public_metrics': tweet['public_metrics'],
                'analysis': analysis
            }
            all_results.append(result)
    
    return {
        'username': username,
        'timestamp': datetime.now().isoformat(),
        'keywords_searched': CONTROVERSIAL_KEYWORDS,
        'total_tweets_found': total_tweets_found,
        'controversial_count': len(controversial_tweets),
        'tweets': all_results,
        'controversial_tweets': controversial_tweets,
        'summary': {
            'total_analyzed': len(all_results),
            'controversial': len(controversial_tweets),
            'non_controversial': len(all_results) - len(controversial_tweets)
        }
    }


def print_console_report(results: Dict):
    """print formatted console report."""
    print(f"\n{'='*60}")
    print("analysis report")
    print(f"{'*'*60}\n")
    
    print(f"profile: @{results['username']}")
    print(f"analysis date: {results['timestamp']}")
    print(f"\nkeywords searched: {len(results['keywords_searched'])}")
    print(f"total tweets found: {results['total_tweets_found']}")
    print(f"tweets analyzed: {results['summary']['total_analyzed']}")
    print(f"controversial tweets: {results['summary']['controversial']}")
    print(f"non-controversial tweets: {results['summary']['non_controversial']}")
    
    if results['controversial_count'] > 0:
        print(f"\n{'='*60}")
        print("controversial tweets")
        print(f"{'='*60}\n")
        
        for idx, tweet in enumerate(results['controversial_tweets'], 1):
            analysis = tweet['analysis']
            print(f"[{idx}] tweet id: {tweet['tweet_id']}")
            print(f"    keyword: {tweet['keyword']}")
            print(f"    date: {tweet['created_at']}")
            print(f"    controversy score: {analysis['controversy_score']}/10")
            print(f"    topics: {', '.join(analysis['topics']) if analysis['topics'] else 'N/A'}")
            print(f"    reasons: {', '.join(analysis['reasons']) if analysis['reasons'] else 'N/A'}")
            print(f"    text: {tweet['text'][:200]}{'...' if len(tweet['text']) > 200 else ''}")
            print(f"    metrics: likes={tweet['public_metrics'].get('like_count', 0)}, "
                  f"retweets={tweet['public_metrics'].get('retweet_count', 0)}")
            print()
    else:
        print(f"\n{'='*60}")
        print("No controversial tweets found.")
        print(f"{'='*60}\n")


def save_json_report(results: Dict, output_file: str):
    """save results to json file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="analyze twitter/x profile for controversial tweets"
    )
    parser.add_argument(
        'username',
        help='twitter username (without @)'
    )
    parser.add_argument(
        '-o', '--output',
        default='output.json',
        help='output json file path (default: output.json)'
    )
    
    args = parser.parse_args()
    
    # load api keys
    twitter_token, openai_key = load_api_keys()
    
    # initialize components
    twitter_searcher = TwitterSearcher(twitter_token)
    analyzer = ControversyAnalyzer(openai_key)
    
    # analyze profile
    results = analyze_profile(args.username, twitter_searcher, analyzer)
    
    # output results
    print_console_report(results)
    save_json_report(results, args.output)
    
    print(f"\nAnalysis complete!")


if __name__ == "__main__":
    main()

