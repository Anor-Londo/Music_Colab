import re
from sys import api_version
from django.conf.urls import url
from django.http.response import JsonResponse
from django.shortcuts import render
from rest_framework import generics, serializers, status
from rest_framework.exceptions import server_error
from .models import Room
from .serializers import RoomSerializer, CreateRoomSerializer, UpdateRoomSerializer
from rest_framework.views import APIView
from rest_framework.response import Response

class RoomView(generics.ListAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

class GetRoom(APIView):
    serializer_class = RoomSerializer
    url_kwarg = 'code'

    def get(self, request, format=None):

        room_code = request.GET.get(self.url_kwarg)
        if room_code != None:
            room = Room.objects.filter(code=room_code)
            if any(room):
                data = RoomSerializer(room[0]).data
                data['is_host'] = self.request.session.session_key == room[0].host
                return Response(data, status=status.HTTP_200_OK)
            return Response({'Room not found': 'Invalid Room Code.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'Bad Request': 'Code parameter not provided'}, status=status.HTTP_400_BAD_REQUEST)


class JoinRoom(APIView):
    url_kwarg = 'code'
    
    def post(self, request, *args, **kwargs):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        
        code = request.data.get(self.url_kwarg)
        if code != None:
            room_result = Room.objects.filter(code=code)
            if any(room_result):
                room = room_result[0]
                self.request.session['room_code'] = code
                return Response({'message': 'Room joined!'}, status=status.HTTP_200_OK)
            return Response({'Room not found': 'Invalid Room Code.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'Bad Request': 'Invalid post data'}, status=status.HTTP_400_BAD_REQUEST)

class CreateRoomView(APIView):
    serializer_class = CreateRoomSerializer

    def post(self, request, *args, **kwargs):
        
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            guest_can_pause = serializer.data.get('guest_can_pause')
            votes_to_skip = serializer.data.get('votes_to_skip')
            host = self.request.session.session_key
            room_query = Room.objects.filter(host=host)

            if room_query.exists():
                room = room_query[0]
                room.guest_can_pause = guest_can_pause
                room.votes_to_skip = votes_to_skip
                room.save(update_fields=['guest_can_pause', 'votes_to_skip'])
                self.request.session['room_code'] = room.code
            else:
                room = Room(guest_can_pause=guest_can_pause, votes_to_skip=votes_to_skip, host=host)
                self.request.session['room_code'] = room.code
                room.save()
        
            return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)

class UserInRoom(APIView):

    def get(self, request, format=None):

        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        room_code = self.request.session.get('room_code')
        data = {'code': room_code}

        return JsonResponse(data, status=status.HTTP_200_OK)

class LeaveRoom(APIView):
    def post(self, request, format=None):
        if 'room_code' in self.request.session:
            self.request.session.pop('room_code')
            host_id = self.request.session.session_key
            room_results = Room.objects.filter(host=host_id)
            if len(room_results) > 0:
                room = room_results[0]
                room.delete()

        return Response({'Message': 'Success'}, status=status.HTTP_200_OK)

class UpdateRoom(APIView):
    def patch(self, request, format=None):

        class_serializer = UpdateRoomSerializer
        serializer = class_serializer(data=request.data)
        if serializer.is_valid():
            guest_can_pause = serializer.data.get('guest_can_pause')
            votes_to_skip = serializer.data.get('votes_to_skip')
            code = serializer.data.get('code')

            room_result = Room.objects.filter(code=code)
            if not room_result.exists():
                return Response({'message': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)
            
            room = room_result[0]
            host_id = self.request.session.session_key
            if room.host != host_id:
                return Response({'message': 'You are not the host!'}, status=status.HTTP_403_FORBIDDEN)
            
            room.guest_can_pause = guest_can_pause
            room.votes_to_skip = votes_to_skip
            room.save(update_fields=['guest_can_pause','votes_to_skip'])
            return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)
        
        return Response({'Bad request': 'Not valid data'}, status=status.HTTP_400_BAD_REQUEST)

