import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface RoomType{
    room_type_id: number,
    is_deleted: boolean,
    created_at: string,
    updated_at: string,
    description:string,
    price_per_night:Number;
    square_ft:Number;
    max_adult_count:Number;
    max_child_count:Number
    type_name:string,
}

@Injectable({providedIn:"root"})

export class RoomTypeService{

private apiUrl=`${environment.apiUrl}/room-management`
constructor(private http:HttpClient){}


getRoomType(room_type_id:number):Observable<RoomType>{
    return this.http.get<RoomType>(`${this.apiUrl}/types/${room_type_id}`)
}

}