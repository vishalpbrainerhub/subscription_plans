# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta


class DeckInherit(models.Model):
    _inherit = 'carddecks.deck'
    
    # Subscription-related fields
    deck_type = fields.Selection([
        ('try_out', 'Try Out'),
        ('free', 'Free'),
        ('premium', 'Premium'),
    ], string='Deck Type', default='free', help='Determines who can access this deck')
    
    # Owner and creation tracking
    creator_user_id = fields.Many2one('res.users', string='Creator', 
                                     default=lambda self: self.env.user,
                                     help='User who created this deck')
    is_user_created = fields.Boolean(string='User Created', default=True,
                                   help='True if created by a user, False if system/admin created')
    
    # Basic tracking
    creation_date = fields.Datetime(string='Creation Date', default=fields.Datetime.now)
    last_played_date = fields.Datetime(string='Last Played')
    play_count = fields.Integer(string='Play Count', default=0)
    
    # Approval system for public decks
    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
    ], string='Approval Status', default='approved')
    

    
    def can_user_access(self, user=None):
        """Check if user can access this deck based on their subscription"""
        if not user:
            user = self.env.user
        
        # Public users (not logged in) - only try_out decks
        if user._is_public():
            return self.deck_type == 'try_out'
        
        # Get user's subscription
        subscription = self.env['user.subscription'].sudo().get_user_subscription(user.id)
        plan_type = subscription.plan_type if subscription else 'free'
        
        # Access based on deck_type and user's plan_type
        if self.deck_type == 'try_out':
            return True  # Everyone can access try_out decks
        elif self.deck_type == 'free':
            return plan_type in ['free', 'premium']  # Free and premium users
        elif self.deck_type == 'premium':
            return plan_type == 'premium'  # Only premium users
        
        return False
    
    def can_user_play(self, user=None):
        """Check if user can play this deck"""
        return self.can_user_access(user) and self.approval_status == 'approved'
    
    def increment_play_count(self):
        """Increment play count and update last played date"""
        self.ensure_one()
        self.play_count += 1
        self.last_played_date = fields.Datetime.now()
    
    @api.model
    def get_accessible_decks(self, user=None, deck_type=None, limit=None):
        """Get decks accessible to user based on subscription"""
        if not user:
            user = self.env.user
        
        # Base domain for public decks (using original carddecks is_public field)
        domain = [
            ('is_public', '=', True),  # Use original carddecks public filtering
        ]
        
        if user._is_public():
            # Public users only see try-out decks
            domain.append(('deck_type', '=', 'try_out'))
        else:
            # Get user's subscription
            subscription = self.env['user.subscription'].sudo().get_user_subscription(user.id)
            plan_type = subscription.plan_type if subscription else 'free'
            
            if plan_type == 'free':
                # Free users see: try-out + free decks
                domain.append(('deck_type', 'in', ['try_out', 'free']))
            elif plan_type == 'premium':
                # Premium users see all deck types
                domain.append(('deck_type', 'in', ['try_out', 'free', 'premium']))
            else:
                # Unknown plan type, only try-out
                domain.append(('deck_type', '=', 'try_out'))
        
        # Add deck type filter if specified
        if deck_type:
            domain.append(('deck_type', '=', deck_type))
        
        return self.search(domain, limit=limit, order='play_count desc')
    
    @api.model
    def get_user_decks(self, user=None):
        """Get decks created by user"""
        if not user:
            user = self.env.user
        
        if user._is_public():
            return self.browse()
        
        return self.search([('creator_user_id', '=', user.id)], order='creation_date desc')
