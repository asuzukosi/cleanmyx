import tweepy
import time
from typing import List, Dict


class TwitterSearcher:
    def __init__(self, bearer_token):
        self.client = tweepy.Client(bearer_token=bearer_token)

    def search_tweets_by_keyword(self, username: str, keyword: str) -> List[Dict]:
        """
        search for tweets from a specific user containing a keyword.
        uses twitter api v2 search_recent_tweets endpoint with pagination.
        args:
            username: Twitter username (without @)
            keyword: keyword to search for
        returns:
            list of tweet dictionaries with text, id, created_at, and public_metrics
        """
        all_tweets = []
        query = f"from:{username} {keyword}"
        
        try:
            # initial search
            response = self.client.search_recent_tweets(
                query=query,
                max_results=100,
                tweet_fields=['created_at', 'public_metrics', 'text'],
                expansions=['author_id']
            )
            print("response: ", response)
            print("response.data: ", response.data)
            if response.data:
                for tweet in response.data:
                    # extract public metrics safely
                    metrics = {}
                    if tweet.public_metrics:
                        metrics = {
                            'like_count': getattr(tweet.public_metrics, 'like_count', 0),
                            'retweet_count': getattr(tweet.public_metrics, 'retweet_count', 0),
                            'reply_count': getattr(tweet.public_metrics, 'reply_count', 0),
                            'quote_count': getattr(tweet.public_metrics, 'quote_count', 0)
                        }
                    
                    all_tweets.append({
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                        'public_metrics': metrics,
                        'keyword': keyword
                    })
            
            # handle pagination
            next_token = response.meta.get('next_token') if response.meta else None
            while next_token:
                try:
                    response = self.client.search_recent_tweets(
                        query=query,
                        max_results=100,
                        tweet_fields=['created_at', 'public_metrics', 'text'],
                        expansions=['author_id'],
                        next_token=next_token
                    )
                    
                    if response.data:
                        for tweet in response.data:
                            # extract public metrics safely
                            metrics = {}
                            if tweet.public_metrics:
                                metrics = {
                                    'like_count': getattr(tweet.public_metrics, 'like_count', 0),
                                    'retweet_count': getattr(tweet.public_metrics, 'retweet_count', 0),
                                    'reply_count': getattr(tweet.public_metrics, 'reply_count', 0),
                                    'quote_count': getattr(tweet.public_metrics, 'quote_count', 0)
                                }
                            
                            all_tweets.append({
                                'id': tweet.id,
                                'text': tweet.text,
                                'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                                'public_metrics': metrics,
                                'keyword': keyword
                            })
                    
                    next_token = response.meta.get('next_token') if response.meta else None
                    
                    # rate limit handling - wait if needed
                    if response.meta and response.meta.get('remaining', 0) == 0:
                        time.sleep(60)  # wait 1 minute if rate limited
                        
                except tweepy.TooManyRequests:
                    # rate limit exceeded, wait and retry
                    time.sleep(60)
                    continue
                except Exception as e:
                    print(f"Error during pagination for keyword '{keyword}': {e}")
                    break
                    
        except tweepy.TooManyRequests:
            print(f"Rate limit exceeded for keyword '{keyword}'. Waiting 60 seconds...")
            time.sleep(60)
        except tweepy.NotFound:
            print(f"User '{username}' not found or no tweets found for keyword '{keyword}'")
        except Exception as e:
            print(f"Error searching tweets for keyword '{keyword}': {e}")
        
        return all_tweets

    def search_tweets_by_keywords_batch(self, username: str, keywords: List[str]) -> List[Dict]:
        """
        search for tweets from a specific user containing any of the provided keywords.
        uses twitter api v2 search_recent_tweets endpoint with OR operators for batch search.
        this is more efficient than multiple separate searches.

        args:
            username: Twitter username (without @)
            keywords: list of keywords to search for
    
        returns:
            list of tweet dictionaries with text, id, created_at, public_metrics, and matched_keywords
        """
        all_tweets = []
        
        # build query with OR operators: from:username (keyword1 OR keyword2 OR ...)
        # escape keywords that might contain special characters
        escaped_keywords = []
        for keyword in keywords:
            # wrap in quotes if keyword contains spaces or special characters
            if ' ' in keyword or any(char in keyword for char in ['"', "'", '(', ')']):
                escaped_keyword = f'"{keyword}"'
            else:
                escaped_keyword = keyword
            escaped_keywords.append(escaped_keyword)
        
        # combine keywords with OR operator
        keywords_query = ' OR '.join(escaped_keywords)
        query = f"from:{username} ({keywords_query})"
        
        print("keywords query:")
        print(keywords_query)
        print(f"query: {query}")
        print(f"executing batch search query with {len(keywords)} keywords...")
        
        try:
            # initial search
            response = self.client.search_recent_tweets(
                query=query,
                max_results=100,
                tweet_fields=['created_at', 'public_metrics', 'text'],
                expansions=['author_id']
            )
            
            if response.data:
                for tweet in response.data:
                    # determine which keywords matched this tweet (case-insensitive)
                    matched_keywords = []
                    tweet_text_lower = tweet.text.lower()
                    for keyword in keywords:
                        if keyword.lower() in tweet_text_lower:
                            matched_keywords.append(keyword)
                    
                    # extract public metrics safely
                    metrics = {}
                    if tweet.public_metrics:
                        metrics = {
                            'like_count': getattr(tweet.public_metrics, 'like_count', 0),
                            'retweet_count': getattr(tweet.public_metrics, 'retweet_count', 0),
                            'reply_count': getattr(tweet.public_metrics, 'reply_count', 0),
                            'quote_count': getattr(tweet.public_metrics, 'quote_count', 0)
                        }
                    
                    all_tweets.append({
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                        'public_metrics': metrics,
                        'matched_keywords': matched_keywords  # list of keywords that matched
                    })
            
            # handle pagination
            next_token = response.meta.get('next_token') if response.meta else None
            while next_token:
                try:
                    response = self.client.search_recent_tweets(
                        query=query,
                        max_results=100,
                        tweet_fields=['created_at', 'public_metrics', 'text'],
                        expansions=['author_id'],
                        next_token=next_token
                    )
                    
                    if response.data:
                        for tweet in response.data:
                            # determine which keywords matched this tweet
                            matched_keywords = []
                            tweet_text_lower = tweet.text.lower()
                            for keyword in keywords:
                                if keyword.lower() in tweet_text_lower:
                                    matched_keywords.append(keyword)
                            
                            # extract public metrics safely
                            metrics = {}
                            if tweet.public_metrics:
                                metrics = {
                                    'like_count': getattr(tweet.public_metrics, 'like_count', 0),
                                    'retweet_count': getattr(tweet.public_metrics, 'retweet_count', 0),
                                    'reply_count': getattr(tweet.public_metrics, 'reply_count', 0),
                                    'quote_count': getattr(tweet.public_metrics, 'quote_count', 0)
                                }
                            
                            all_tweets.append({
                                'id': tweet.id,
                                'text': tweet.text,
                                'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                                'public_metrics': metrics,
                                'matched_keywords': matched_keywords
                            })
                    
                    next_token = response.meta.get('next_token') if response.meta else None
                    
                    # rate limit handling - wait if needed
                    if response.meta and response.meta.get('remaining', 0) == 0:
                        time.sleep(60)  # wait 1 minute if rate limited
                        
                except tweepy.TooManyRequests:
                    # rate limit exceeded, wait and retry
                    time.sleep(60)
                    continue
                except Exception as e:
                    print(f"error during pagination: {e}")
                    break
                    
        except tweepy.TooManyRequests:
            print(f"rate limit exceeded. waiting 60 seconds...")
            time.sleep(60)
        except tweepy.BadRequest as e:
            # query might be too long, fall back to individual searches
            print(f"batch query failed (possibly too long): {e}")
            raise  # re-raise to signal fallback needed
        except tweepy.NotFound:
            print(f"user '{username}' not found or no tweets found")
        except Exception as e:
            print(f"error searching tweets: {e}")
        
        return all_tweets

    def validate_user(self, username: str) -> bool:
        """
        validate that a twitter user exists.
        args:
            username: Twitter username (without @)
        returns:
            bool: True if user exists, False otherwise
        """
        try:
            user_response = self.client.get_user(username=username)
            return user_response.data is not None
        except tweepy.NotFound:
            return False
        except Exception as e:
            print(f"Error validating user '{username}': {e}")
            return False